Heka Configuration
--------------------

To assist with getting a working Heka set up, heka-py provides a
:doc:`api/config` module which will take declarative configuration info in
either ini file or python dictionary format and use it to configure a
HekaClient instance. Even if you choose not to use these configuration
helpers, this document provides a good overview of the configurable options
provided by default by the :doc:`api/client` client class.

The config module will accept configuration data either in ini format (as a
text value or a stream input) or as a Python dictionary value. This document
will first describe the supported ini file format, followed by the
corresponding dictionary format to which the ini format is ultimately
converted behind the scenes.

INI format
==========

The primary `HekaClient` configuration should be provided in a `heka`
section of the provided ini file text. (Note that the actual name of the
section is passed in to the config parsing function, so it can be any legal ini
file section name, but for illustration purposes these documents will assume
that the section name is `heka`.) A sample `heka` section might look like
this::

  [heka]
  logger = myapp
  severity = 4
  disabled_timers = foo
                    bar
  stream_class = heka.streams.UdpStream
  stream_host = localhost
  stream_port = 5565

Of all of these settings, only `stream_class` is strictly required. A detailed
description of each option follows:

logger
  Each heka message that goes out contains a `logger` value, which is simply
  a string token meant to identify the source of the message, usually the
  name of the application that is running. This can be specified separately for
  each message that is sent, but the client supports a default value which will
  be used for all messages that don't explicitly override. The `logger` config
  option specifies this default value. This value isn't strictly required, but
  if it is omitted '' (i.e. the empty string) will be used, so it is strongly
  suggested that a value be set.

severity
  Similarly, each heka message specifies a `severity` value corresponding to
  the integer severity values defined by `RFC 3164
  <https://www.ietf.org/rfc/rfc3164.txt>`_. And, again, while each message can
  set its own severity value, if one is omitted the client's default value will
  be used. If no default is specified here, the default default (how meta!)
  will be 6, "Informational".

disabled_timers
  Heka natively supports "timer" behavior, which will calculate the amount of
  elapsed time taken by an operation and send that data along as a message to
  the back end. Each timer has a string token identifier. Because the act of
  calculating code performance actually impacts code performance, it is
  sometimes desirable to be able to activate and deactivate timers on a case by
  case basis. The `disabled_timers` value specifies a set of timer ids for
  which the client should NOT actually generate messages. Heka will attempt
  to minimize the run-time impact of disabled timers, so the price paid for
  having deactivated timers will be very small. Note that the various timer ids
  should be newline separated.

stream_class
  This should be a Python dotted notation reference to a class (or factory
  function) for a Heka "stream" object. A stream needs to provide a
  `write(data)` method, which is responsible for accepting a byte
  serialized message and passing it along to the router / back end /
  output mechanism / etc. heka-py provides some development streams,
  but the main one it provides for intended production use makes use
  of UDP to send messages to any configured listeners.

stream_* (excluding stream_class)
  As you might guess, different types of streams can require different
  configuration values. Any config options other than `stream_class` that start
  with `stream_` will be passed to the stream factory as keyword arguments,
  where the argument name is the option name minus the `stream_` component and
  the value is the specified value. In the example above, the UDP host
  and port will be passed to the UdpStream constructor.

encoder:
  This should be a Python dotted notation reference to a class (or
  factory function) for a Heka "encoder" object.  An encoder needs to
  provider a `encode(msg)` method which is responsible for serializing
  an instance of heka.message.Message and returning a byte serialized
  version of the message.  Currently implemented encoders are
  JSONEncoder and ProtobufEncoder.

  If no encoder is specified, the JSONEncoder is used by default.


In addition to the main `heka` section, any other config sections that start
with `heka_` (or whatever section name is specified) will be considered to be
related to the heka installation. Only specific variations of these are
supported, however. The first of these is configuration for HekaClient
:doc:`api/filters`. Here is an example of such a configuration::

  [heka_filter_sev_max]
  provider = heka.filters.severity_max_provider
  severity = 4

  [heka_filter_type_whitelist]
  provider = heka.filters.type_whitelist_provider
  types = timer
          oldstyle

Each `heka_filter_*` section must contain a `provider` entry, which is a
dotted name specifying a filter provider function. The rest of the options in
that section will be converted into configuration parameters. The provider
function will be called and passed the configuration parameters, returning a
filter function that will be added to the client's filters. The filters will be
applied in the order they are specified. In this case a "severity max" filter
will be applied, so that only messages with a severity of 4 (i.e. "warning") or
lower will actually be passed in to the stream. Additionally a "type whitelist"
will be applied, so that only messages of type "timer" and "oldstyle" will be
delivered.

HMAC signatures
===============

Messages can be signed with an HMAc.  You may use either SHA1 or MD5
to sign messages.

The INI configuration looks for a section that is the same as your
client, but is post-fixed with "_hmac".

An example configuration in INI format looks like ::

    [heka]
    stream_class = heka.streams.DebugCaptureStream

    [heka_hmac]
    signer = some_signer_name
    key_version = 2
    hash_function = SHA1
    key = some_key_value

All HMAC signatures and metadata are stored in the Heka header to be
decoded by a heka daemon.

Plugins
-------

Heka allows you to bind new extensions onto the client through a plugin
mechanism.

Each plugin must have a configuration section name with a prefix of
`heka_plugin_`.  Configuration is parsed into a dictionary, passed into a
configurator and then the resulting plugin method is bound to the client.

Each configuration section for a plugin must contain at least one option with
the name `provider`. This is a dotted name for a function which will be used to
configure a plugin.  The return value for the provider is a configured method
which will then be bound into the Heka client.

Each plugin extension method has a canonical name that is bound to the
heka client as a method name. The suffix that follows the
`heka_plugin_` prefix is used only to distinguish logical sections
for each plugin within the configuration file.

An example best demonstrates what can be expected.  To load the dummy plugin,
you need a `heka_plugin_dummy` section as well as some configuration
parameters. Here's an example ::

    [heka_plugin_dummysection]
    provider=heka.tests.plugin.config_plugin
    port=8080
    host=localhost

Once you obtain a reference to a client, you can access the new method. ::

    from heka.holder import CLIENT_HOLDER
    client = CLIENT_HOLDER.get_client('your_app_name')
    client.dummy('some', 'ignored', 'arguments', 42)


Message Encoders
----------------

NullEncoder
===========

This encoder passes protocol buffer objects through the encode()
function.  This is only used for debugging purposes

JSONEncoder
===========

This is the default encoder.  Messages are serialized to JSON and then
prefixed with a protocol buffer header.

StdlibPayloadEncoder
====================

The StdlibPayloadEncoder *must* be used in conjunction with the
StdLibLoggingStream.  This encoder is a lossy output stream which only
writes out the payload section to the Python logger.

ProtobufEncoder
===============

The ProtobufEncoder writes messages using raw protocol buffers.  Note
that a small protocol buffer header is also prefixed to the message so
that the hekad daemon can decode the message.

Output streams
--------------

All streams are visible under the `heka.streams` namespace.

DebugCaptureStream 
===================

This stream captures messages and stores them in a `msgs` queue.  Note
that the encoder you use may make it awkward to read messages out of
the queue.  You can use the NullEncoder for testing purposes which
will simply queue up the protocol buffer objects for you.

Example config ::

    [heka]
    stream_class = heka.streams.DebugCaptureStream
    encoder = heka.encoders.ProtobufEncoder

FileStream
==========

This stream appends messages to a file. 

Example config ::

    [heka]
    stream_class = heka.streams.DebugCaptureStream


StdOutStream
============

This stream captures messages and writes them to stdout.

Example config ::

    [heka]
    stream_class = heka.streams.StdOutStream


StdLibLoggingStream
===================

This stream captures messages and writes them to the python standard
logger.  Currently = you *must* use the StdlibJSONEncoder with this
output stream.

Example configuration ::

    [heka]
    stream_class = heka.streams.StdLibLoggingStream
    stream_logger_name = HekaLogger
    encoder = heka.encoders.StdlibJSONEncoder

TcpStream
=========

The TcpStream writes messages to one or more hosts. There is currently
minimal support for error handling if a socket is closed on the the
remote host.

Example ::

    [heka]
    stream_class = heka.streams.TcpStream
    stream_host = 192.168.20.2
    stream_port = 5566

UdpStream 
==========

The UdpStream writes messages to one or more hosts. 

Example ::

    [heka]
    stream_class = heka.streams.UdpStream
    stream_host = 192.168.20.2
    stream_port = 5565

Examples
--------

Working examples are included in the examples directory in the git
repository for you.


Dictionary Format
-----------------

When using the `client_from_text_config` or `client_from_stream_config`
functions of the config module to parse an ini format configuration, heka-py
simply converts these values to a dictionary which is then passed to
`client_from_dict_config`. If you choose to not use the specified ini format,
you can parse configuration yourself and call `client_from_dict_config`
directly. The configuration specified in the "ini format" section above would
be converted to the following dictionary::

  {'logger': 'myapp',
   'severity': 4,
   'disabled_timers': ['foo', 'bar'],
   'stream': {'class': 'heka.streams.UdpStream',
              'host': 'localhost',
              'port': 5565,
    },
   'filters': [('heka.filters.severity_max',
                {'severity': 4},
               ),
               ('heka.filters.type_whitelist',
                {'types': ['timer', 'oldstyle']},
               ),
              ],
  }

To manually load a Heka client with plugins, the `client_from_dict_config`
function allows you to pass in a list of plugin configurations using the
`plugins` dict key, used in the same fashion as `filters` in the example
directly above.

The configuration specified in the "plugins" section above would be converted
into the following dictionary, where the key will be the name of the method
bound to the client::

    {'dummy': ('heka.tests.plugin:config_plugin',
               {'port': 8080,
                'host': 'localhost'
               },
              )
    }


Debugging your configuration
----------------------------

You may find yourself with a heka client which is not behaving
in a manner that you expect.  Heka provides a deepcopy of the
configuration that was used when the client was instantiated for
debugging purposes.

The following code shows how you can verify that the configuration
used is actually what you expect it to be ::

    import json
    from heka.config import client_from_dict_config

    cfg = {'logger': 'addons-marketplace-dev',
           'stream': {'class': 'heka.streams.UdpStream',
           'host': ['logstash1', 'logstash2'],
           'port': '5566'}}
    client = client_from_dict_config(cfg)
    assert client._config == json.dumps(cfg)
