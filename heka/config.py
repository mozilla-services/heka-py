# ***** BEGIN LICENSE BLOCK *****
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this file,
# You can obtain one at http://mozilla.org/MPL/2.0/.
#
# Contributor(s):
#   Rob Miller (rmiller@mozilla.com)
#   Victor Ng (vng@mozilla.com)
#
# ***** END LICENSE BLOCK *****
"""Helpers to handle HekaClient configuration details."""
import ConfigParser
import StringIO
import copy
import json
import os
import re

from textwrap import dedent

from heka.client import HekaClient
from heka.exceptions import EnvironmentNotFoundError
from heka.path import DottedNameResolver

_IS_INTEGER = re.compile('^-?[0-9].*')
_IS_ENV_VAR = re.compile('\$\{(\w.*)?\}')


def _get_env_val(match_obj):
    var = match_obj.groups()[0]
    if var not in os.environ:
        raise EnvironmentNotFoundError(var)
    return os.environ[var]


def _convert(value):
    """Converts a config value. Numeric integer strings are converted to
    integer values.  'True-ish' string values are converted to boolean True,
    'False-ish' to boolean False. Any alphanumeric (plus underscore) value
    enclosed within ${dollar_sign_curly_braces} is assumed to represent an
    environment variable, and will be converted to the corresponding value
    provided by os.environ.
    """
    def do_convert(value):
        if not isinstance(value, basestring):
            # we only convert strings
            return value

        value = value.strip()
        if _IS_INTEGER.match(value):
            try:
                return int(value)
            except ValueError:
                pass
        elif value.lower() in ('true', 't', 'on', 'yes'):
            return True
        elif value.lower() in ('false', 'f', 'off', 'no'):
            return False
        match_obj = _IS_ENV_VAR.match(value)
        if match_obj:
            return _get_env_val(match_obj)
        return value

    if isinstance(value, basestring) and '\n' in value:
        return [line for line in [do_convert(line)
                                  for line in value.split('\n')]
                if line.strip() != '']

    return do_convert(value)


def nest_prefixes(config_dict, prefixes=None, separator="_"):
    """
    Iterates through the `config_dict` keys, looking for any starting w/ one of
    a specific set of prefixes, moving those into a single nested dictionary
    keyed by the prefix value.

    :param config_dict: Dictionary to mutate. Will also be returned.
    :param prefixes: Sequence of prefixes to look for in `config_dict` keys.
    :param separator: String which separates prefix values from the rest of the
                      key.
    """
    if prefixes is None:
        prefixes = ['stream']
    for prefix in prefixes:
        prefix_dict = {}
        for key in config_dict.keys():
            full_prefix = prefix + separator
            if key.startswith(full_prefix):
                nested_key = key[len(full_prefix):]
                prefix_dict[nested_key] = config_dict[key]
        if prefix_dict:
            if prefix in config_dict:
                config_dict[prefix].update(prefix_dict)
            else:
                config_dict[prefix] = prefix_dict
    return config_dict


def client_from_dict_config(config, client=None):
    """
    Configure a heka client, fully configured w/ stream and plugins.

    :param config: Configuration dictionary.
    :param client: HekaClient instance to configure. If None, one will be
                   created.

    The configuration dict supports the following values:

    logger
      Heka client default logger value.
    severity
      Heka client default severity value.
    disabled_timers
      Sequence of string tokens identifying timers that are to be deactivated.
    filters
      Sequence of 2-tuples `(filter_provider, config)`. Each `filter_provider`
      is a dotted name referring to a function which, when called and passed
      the associated `config` dict as kwargs, will return a usable HekaClient
      filter function.
    plugins
      Nested dictionary containing plugin configuration. Keys are the plugin
      names (i.e. the name the method will be given when attached to the
      client). Values are 2-tuples `(plugin_provider, config)`. Each
      `plugin_provider` is a dotted name referring to a function which, when
      called and passed the associated `config`, will return the usable plugin
      method.
    stream
      Nested dictionary containing stream configuration.

    All of the configuration values are optional, but failure to include a
    stream may result in a non-functional Heka client. Any unrecognized keys
    will be ignored.

    Note that any top level config values starting with `stream_` will be added
    to the `stream` config dictionary, overwriting any values that may already
    be set.

    The stream configuration supports the following values:

    class (required)
      Dotted name identifying the stream class to instantiate.
    args
      Sequence of non-keyword args to pass to stream constructor.
    <kwargs>
      All remaining key-value pairs in the stream config dict will be passed as
      keyword arguments to the stream constructor.
    """
    # Make a deep copy of the configuration so that subsequent uses of
    # the config won't blow up
    config = nest_prefixes(copy.deepcopy(config))
    config_copy = json.dumps(copy.deepcopy(config))

    stream_config = config.get('stream', {})

    logger = config.get('logger', '')
    severity = config.get('severity', 6)
    disabled_timers = config.get('disabled_timers', [])
    filter_specs = config.get('filters', [])
    plugins_data = config.pop('plugins', {})
    encoder = config.get('encoder', 'heka.encoders.ProtobufEncoder')
    hmc = config.get('hmac', {})

    resolver = DottedNameResolver()

    # instantiate stream
    stream_clsname = stream_config.pop('class')
    stream_cls = resolver.resolve(stream_clsname)
    stream_args = stream_config.pop('args', tuple())
    stream = stream_cls(*stream_args, **stream_config)

    # initialize filters
    filters = [resolver.resolve(dotted_name)(**cfg)
               for (dotted_name, cfg) in filter_specs]


    if client is None:
        client = HekaClient(stream,
                            logger,
                            severity,
                            disabled_timers,
                            filters, 
                            encoder=encoder,
                            hmc=hmc)
    else:
        client.setup(stream, encoder, hmc, logger, severity, disabled_timers, filters)

    # initialize plugins and attach to client
    for section_name, plugin_spec in plugins_data.items():
        # each plugin spec is a 2-tuple: (dotted_name, cfg)
        plugin_config = plugin_spec[1]
        plugin_override = plugin_config.pop('override', False)
        plugin_fn = resolver.resolve(plugin_spec[0])(plugin_config)
        client.add_method(plugin_fn, plugin_override)

    # We bind the configuration into the client itself to ease
    # debugging
    client._config = config_copy
    return client


def dict_from_stream_config(stream, section):
    """
    Parses configuration from a stream and converts it to a dictionary suitable
    for passing to `client_from_dict_config`.

    :param stream: Stream object containing config information.
    :param section: INI file section containing the configuration we care
                    about.
    """
    config = ConfigParser.SafeConfigParser()
    config.readfp(stream)
    client_dict = {}

    # extract main client configuration
    for opt in config.options(section):
        client_dict[opt] = _convert(config.get(section, opt))

    # extract filter config from filter sections
    filters = []
    filter_sections = [n for n in config.sections()
                       if n.startswith('%s_filter' % section)]
    for filter_section in filter_sections:
        filter_config = {}
        for opt in config.options(filter_section):
            if opt == 'provider':
                # must be a dotted name string, don't convert
                dotted_name = config.get(filter_section, opt)
            else:
                filter_config[opt] = _convert(config.get(filter_section, opt))
        filters.append((dotted_name, filter_config))
    client_dict['filters'] = filters

    # extract plugin config from plugin sections
    plugins = {}
    plugin_sections = [n for n in config.sections()
                       if n.startswith("%s_plugin" % section)]
    for plugin_section in plugin_sections:
        plugin_name = plugin_section.replace("%s_plugin_" % section, '')
        plugin_config = {}
        provider = ''
        for opt in config.options(plugin_section):
            if opt == 'provider':
                # must be a dotted name string, don't convert
                provider = config.get(plugin_section, opt)
            else:
                plugin_config[opt] = _convert(config.get(plugin_section, opt))
        plugins[plugin_name] = (provider, plugin_config)
    client_dict['plugins'] = plugins

    # extract hmac config from hmac sections
    hmc = {}
    hmac_section = "%s_hmac" % section
    if config.has_section(hmac_section):
        hmc['signer'] = config.get(hmac_section, 'signer')
        hmc['key_version'] = config.get(hmac_section, 'key_version')
        hmc['hash_function'] = config.get(hmac_section, 'hash_function')
        hmc['key']  = config.get(hmac_section, 'key')

    client_dict['hmac'] = hmc

    client_dict = nest_prefixes(client_dict)
    return client_dict


def client_from_stream_config(stream, section, client=None):
    """
    Extract configuration data in INI format from a stream object (e.g. a file
    object) and use it to generate a Heka client. Config values will be sent
    through the `_convert` function for possible type conversion.

    :param stream: Stream object containing config information.
    :param section: INI file section containing the configuration we care
                    about.
    :param client: HekaClient instance to configure. If None, one will be
                   created.

    Note that all stream config options should be prefaced by "stream_", e.g.
    "stream_class" should specify the dotted name of the stream class to use.
    Similarly all extension method settings should be prefaced by
    "extensions_".
    """
    client_dict = dict_from_stream_config(stream, section)
    client = client_from_dict_config(client_dict, client)
    return client


def client_from_text_config(text, section, client=None):
    """
    Extract configuration data in INI format from provided text and use it to
    configure a Heka client. Text is converted to a stream and passed on to
    `client_from_stream_config`.

    :param text: INI text containing config information.
    :param section: INI file section containing the configuration we care
                    about.
    :param client: HekaClient instance to configure. If None, one will be
                   created.
    """
    stream = StringIO.StringIO(dedent(text))
    return client_from_stream_config(stream, section, client)
