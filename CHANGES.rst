0.30.1 - 2013-08-16
===================
- throw errors if None is passed into the 'fields' dictionary of the
  of client.heka()

0.30 - 2013-06-25
=================
- minor updates to the ProtocolBuffer protocol to match hekad 0.3

0.20 - 2013-04-26
=================
- a completely reworked wire level protocol has been implemented to
  match hekad 0.2
- timestamps formats have been changed to nanoseconds from UTC epoch.
- uuid per message
- protocol buffers!
- tcp support!
- message signing support
- refactored the senders into streams and encoders so that you can
  pick from (UDP|TCP) with (JSON|ProtocolBuffer)

_ 
0.10 - 2013-03-12
==================
- rename package from metlog-py to heka-py
- refactor conditional imports to single util module

0.9.10 - 2012-12-28
==================
- changed the _config attribute to be a flat json string for simpler
  debugging in production systems

0.9.9 - 2012-12-18
==================

- Added a _config attribute on the client instance so you can inspect
  the actual configuration that is in play.

0.9.8 - 2012-10-05
==================

- HekaClient now accepts single string values for the `disabled_timers`
  argument.
- Fixed bug where timer wouldn't be disabled if the function name didn't match
  the timer name.
- Added better error handling for invalid unicode. Unserializable
  messages will now get routed to stderr
- A new heka benchmark command line utility (mb) is now included


0.9.7 - 2012-09-11
==================

- Fixed a bug where `client_from_dict_config` would mutate the input
  configuration causing subsequent use of the configuration to fail.

0.9.6 - 2012-09-11
==================

- Couple of bug fixed in decorator base class.
- Added support for UdpSender to have multiple listener hosts.


0.9.5 - 2012-08-14
==================

- Properly handle 'self' arguments when decorators are used on a method.
- Only apply string formatting to 'oldstyle' messages if string formatting args
  are actually provided.

0.9.4 - 2012-07-25
==================

- Added a testcase against the UDP input plugin.
- Fixed bug in socket.sendto function signature.

0.9.3 - 2012-07-18
==================

- HekaClient's `override` argument now accepts method name to override
  instead of `True`.
- Decorator tests now get the expected envelope version from the module source
  code rather than hard coded in the tests.
- Added udp sender.

0.9.2 - 2012-06-22
==================

- Plugin method names are now expected to be stored in the `heka_name`
  attribute of the provided function rather than passed in separately.
- 'oldstyle' messages now support string substitution using provided args and
  the `exc_info` keyword argument for slightly better stdlib logging
  compatibility.
- ZeroMQ sender now uses gevent safe implementations of `Queue` class and `zmq`
  module if the gevent monkeypatches have been applied.

0.9.1 - 2012-06-08
==================

- Added `StdLibLoggingSender` that delegates message delivery to Python's
  standard library `logging` module.

0.9 - 2012-05-31
================

- Refactored / simplified filter and plug-in config loading code
- Filter functions now use closures for filter config (matching plug-in config)
  instead of passing the config as an argument each time.
- `HekaClient.add_method` now supports `override` argument to force the issue
  of replacing existing attributes.
- Added `heka_hostname` and `heka_pid` to the message envelope handed to the
  sender.
- Added support for `rate` argument to `HekaClient.incr` method.
- `HekaClient.timer` converted from a property to a method, allowing for much
  better performance and much simpler code.
- Got rid of `new_default` argument `HekaClientHolder.delete_client`. Folks
  can set a new default w/ another function call if necessary.
- `DebugCaptureSender.__init__` now accepts arbitrary keyword args and stores
  them as attributes on the instance to allow for easier testing of the config
  parsing code.

0.8.5 - 2012-05-07
==================

- Replaced `heka.decorators.base.HekaClientWrapper` with
  `heka.holder.HekaClientHolder` which is a bit more useful and a bit more
  sane.
- Moved Python stdlib `logging` compatibility hooks into its own module.
- Updated config parsing to support global values stored in the CLIENT_HOLDER.
- Added `is_active` property to `HekaClient`.
- Heavily revised "Getting Started" documentation.
- Added `dict_from_stream_config` function to `config`.
- Extracted `StreamSender` from `StdOutServer`, added support for arbitrary
  formatters for the output.
- Added `ZmqHandshakePubSender` which communicates w/ clients via a control
  channel.
- ZMQ senders now use connection pooling.

0.8.4 - 2012-04-18
==================

- "Getting started" documentation
- Overall documentation ToC
- Added Heka stdlib logging handler so logging in dependency libraries can be
  routed to Heka
- Use 0mq connection pool instead of creating a new 0mq connection for each new
  thread
- Initial implementation of 0mq "Handshaking Client" which will use a separate
  control channel to establish communication with 0mq subscribers.
- Added `debug_stderr` flag to ZmqPubSender which will also send all output to
  stderr for capturing output when error messages aren't getting through to the
  Heka listener.

0.8.3 - 2012-04-05
==================

- Added support for simple message filtering directly in the heka client
- "Heka Configuration" documentation
- Added support for setting up client extension methods from configuration

0.8.2 - 2012-03-22
==================

- Added `config`, `decorators`, and `exceptions` to sphinx API docs
- Support for passing a client in to the `client_from_*` functions
  to reconfigure an existing client instead of creating a new one
- Docstring / documentation improvements
- Added `reset` method to `HekaClientWrapper`
- Add support for keeping track of applied decorators to `HekaDecorator`
  class
- Added `NoSendSender` class for use when a client is create w/o a sender

0.8.1 - 2012-03-01
==================

- Support for specific timers to be disabled
- Support for dynamic extension methods to be added to HekaClient
- "Classic" logger style API added to HekaClient
- Helper code added to create client and sender from configuration data
- Support for "deferred" decorators that don't actually bind to the wrapped
  function until after Heka configuration can be loaded
- `timeit` and `incr_count` deferred decorators provided
- Stole most of `pyramid.path`
- README file is now used as package `long_description` value

0.8 - 2012-02-13
================

- Initial release
