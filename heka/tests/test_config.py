# ***** BEGIN LICENSE BLOCK *****
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this file,
# You can obtain one at http://mozilla.org/MPL/2.0/.
#
# The Initial Developer of the Original Code is the Mozilla Foundation.
# Portions created by the Initial Developer are Copyright (C) 2012
# the Initial Developer. All Rights Reserved.
#
# Contributor(s):
#   Rob Miller (rmiller@mozilla.com)
#
# ***** END LICENSE BLOCK *****
from heka.client import HekaClient
from heka.config import client_from_dict_config
from heka.config import client_from_text_config
from heka.exceptions import EnvironmentNotFoundError
from heka.message import Message
from heka.streams import DebugCaptureStream
from mock import Mock
from nose.tools import assert_raises, eq_, ok_
import json
import os

# sys is used in a mock patch, so flake8 may yell at you
import sys  # NOQA


MockStream = Mock()


def test_simple_config():
    cfg_txt = """
    [heka_config]
    stream_class = heka.streams.DebugCaptureStream
    """
    client = client_from_text_config(cfg_txt, 'heka_config')
    eq_(client.__class__, HekaClient)
    eq_(client.stream.__class__.__name__, 'DebugCaptureStream')


def test_multiline_config():
    cfg_txt = """
    [heka_config]
    stream_class = heka.tests.test_config.MockStream
    stream_multi = foo
                   bar
    """
    client = client_from_text_config(cfg_txt, 'heka_config')
    ok_(isinstance(client.stream, Mock))
    MockStream.assert_called_with(multi=['foo', 'bar'])


def test_environ_vars():
    env_var = 'SENDER_TEST'
    marker = object()
    orig_value = marker
    if env_var in os.environ:
        orig_value = os.environ[env_var]
    os.environ[env_var] = 'heka.streams.DebugCaptureStream'
    cfg_txt = """
    [test1]
    stream_class = ${SENDER_TEST}
    """
    client = client_from_text_config(cfg_txt, 'test1')
    eq_(client.stream.__class__, DebugCaptureStream)

    cfg_txt = """
    [test1]
    stream_class = ${NO_SUCH_VAR}
    """
    assert_raises(EnvironmentNotFoundError, client_from_text_config,
                  cfg_txt, 'test1')
    if orig_value is not marker:
        os.environ[env_var] = orig_value
    else:
        del os.environ[env_var]


def test_int_bool_conversions():
    cfg_txt = """
    [heka_config]
    stream_class = heka.tests.test_config.MockStream
    stream_integer = 123
    stream_true1 = True
    stream_true2 = t
    stream_true3 = Yes
    stream_true4 = on
    stream_false1 = false
    stream_false2 = F
    stream_false3 = no
    stream_false4 = OFF
    """
    client = client_from_text_config(cfg_txt, 'heka_config')
    ok_(isinstance(client.stream, Mock))
    MockStream.assert_called_with(integer=123, true1=True, true2=True,
                                  true3=True, true4=True, false1=False,
                                  false2=False, false3=False, false4=False)


def test_filters_config():
    cfg_txt = """
    [heka]
    stream_class = heka.streams.DebugCaptureStream
    [heka_filter_sev_max]
    provider = heka.filters.severity_max_provider
    severity = 6
    [heka_filter_type_whitelist]
    provider = heka.filters.type_whitelist_provider
    types = foo
            bar
            baz
    """
    client = client_from_text_config(cfg_txt, 'heka')
    eq_(len(client.filters), 2)

    severity_max = [x for x in client.filters if x.func_name == 'severity_max']
    eq_(len(severity_max), 1)
    severity_max = severity_max[0]
    eq_(severity_max.func_name, 'severity_max')
    msg = Message(severity=6)
    ok_(severity_max(msg))
    msg = Message(severity=7)
    ok_(not severity_max(msg))

    type_whitelist = [x for x in client.filters
                      if x.func_name == 'type_whitelist']
    eq_(len(type_whitelist), 1)
    type_whitelist = type_whitelist[0]
    eq_(type_whitelist.func_name, 'type_whitelist')
    msg = Message(type='bar')
    ok_(type_whitelist(msg))
    msg = Message(type='bawlp')
    ok_(not type_whitelist(msg))


def test_plugins_config():
    cfg_txt = """
    [heka]
    stream_class = heka.streams.DebugCaptureStream
    [heka_plugin_dummy]
    provider=heka.tests.plugin:config_plugin
    verbose=True
    foo=bar
    some_list = dog
                cat
                bus
    port=8080
    host=lolcathost
    """
    client = client_from_text_config(cfg_txt, 'heka')
    actual = client.dummy(verbose=True)
    expected = {'host': 'lolcathost',
                'foo': 'bar',
                'some_list': ['dog', 'cat', 'bus'],
                'port': 8080}
    eq_(actual, expected)


def test_plugin_override():
    cfg_txt = """
    [heka]
    stream_class = heka.streams.DebugCaptureStream

    [heka_plugin_exception]
    override=True
    provider=heka.tests.plugin:config_plugin
    """
    client = client_from_text_config(cfg_txt, 'heka')
    eq_('dummy', client.dummy.heka_name)

    cfg_txt = """
    [heka]
    stream_class = heka.streams.DebugCaptureStream
    [heka_plugin_exception]
    provider=heka.tests.plugin_exception:config_plugin
    """
    # Failure to set an override argument will throw an exception
    assert_raises(SyntaxError, client_from_text_config, cfg_txt, 'heka')


def test_load_config_multiple_times():
    """
    This used to crash because of pop() operations
    """
    cfg = {'logger': 'addons-marketplace-dev',
           'stream': {'class': 'heka.streams.UdpStream',
                      'host': ['logstash1', 'logstash2'],
                      'port': '5566'},
           }

    client_from_dict_config(cfg)
    client_from_dict_config(cfg)


def test_clients_expose_configuration():
    cfg = {'logger': 'addons-marketplace-dev',
           'stream': {'class': 'heka.streams.UdpStream',
                      'host': ['logstash1', 'logstash2'],
                      'port': '5566'},
           }

    client = client_from_dict_config(cfg)
    eq_(client._config, json.dumps(cfg))


def test_configure_with_hmac():
    cfg_txt = """
    [heka_config]
    stream_class = heka.streams.DebugCaptureStream

    [heka_config_hmac]
    signer = some_signer_name
    key_version = 2
    hash_function = SHA1
    key = some_key_value

    """
    client = client_from_text_config(cfg_txt, 'heka_config')
    eq_(client.__class__, HekaClient)
    expected_hmc = {'hash_function': 'SHA1',
                    'key_version': '2',
                    'key': 'some_key_value',
                    'signer': 'some_signer_name'}
    eq_(client.encoder.hmc, expected_hmc)
