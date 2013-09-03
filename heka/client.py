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
#   James Socol (james@mozilla.com)
#   Victor Ng (vng@mozilla.com)
#
# ***** END LICENSE BLOCK *****
from __future__ import absolute_import
from functools import wraps
import os
import random
import socket
import sys
import threading
import time
import traceback
import types
import uuid
import datetime

from heka.message_pb2 import Message, Field

class SEVERITY:
    """Put a namespace around RFC 3164 syslog messages"""
    EMERGENCY = 0
    ALERT = 1
    CRITICAL = 2
    ERROR = 3
    WARNING = 4
    NOTICE = 5
    INFORMATIONAL = 6
    DEBUG = 7


class _NoOpTimer(object):
    """A bogus timer object that will act as a contextdecorator but
    which doesn't actually do anything.

    """
    def __init__(self):
        self.start = None
        self.result = None

    def __call__(self, fn):
        return fn

    def __enter__(self):
        return self

    def __exit__(self, typ, value, tb):
        return False


class _Timer(object):
    """A contextdecorator for timing."""
    def __init__(self, client, name, msg_data):
        # most attributes on a _Timer object should be threadlocal, except for
        # a few which we put directly in the __dict__
        self.__dict__['client'] = client
        self.__dict__['_local'] = threading.local()
        self.__dict__['name'] = name
        self.msg_data = msg_data

    def __delattr__(self, attr):
        """Store thread-local data safely."""
        delattr(self._local, attr)

    def __getattr__(self, attr):
        """Store thread-local data safely."""
        return getattr(self._local, attr)

    def __setattr__(self, attr, value):
        """Store thread-local data safely."""
        setattr(self._local, attr, value)

    def __call__(self, fn):
        """Support for use as a decorator."""
        if not callable(fn):
            # whoops, can't decorate if we're not callable
            raise ValueError('Timer objects can only wrap callable objects.')

        @wraps(fn)
        def wrapped(*a, **kw):
            with self:
                return fn(*a, **kw)
        return wrapped

    def __enter__(self):
        self.start = time.time()
        self.result = None
        return self

    def __exit__(self, typ, value, tb):
        elapsed = time.time() - self.start
        elapsed = int(round(elapsed * 1000))  # Convert to ms.
        self.result = elapsed
        self.client.timer_send(self.name, elapsed, **self.msg_data)
        return False


class HekaClient(object):
    """Client class encapsulating heka API, and providing storage for
    default values for various heka call settings.

    """
    # envelope version, only changes when the message format changes
    env_version = '0.8'

    def __init__(self, stream, logger, severity=6,
                 disabled_timers=None, filters=None,
                 encoder='heka.encoders.ProtobufEncoder', 
                 hmc=None):
        """Create a HekaClient

        :param stream:  A string denoting which transport will be
                        used for actual message delivery. (udp|tcp)
        :param encoder : A string denoting which encoder will be
                         used.  (protobuf)

        :param logger: Default `logger` value for all sent messages.
                       This is commonly set to be the name of the
                       current application and is not modified for
                       different instances of heka within the
                       scope of the same application.
        :param severity: Default `severity` value for all sent
                         messages.
        :param disabled_timers: Sequence of string tokens identifying
                                timers that should be deactivated.
        :param filters: A sequence of filter callables.
        :param hmc : A hashmac function

        """


        self.setup(stream, encoder, hmc, logger, severity, disabled_timers, filters)

        self._dynamic_methods = {}
        self._timer_obs = {}
        self._noop_timer = _NoOpTimer()
        self.hostname = socket.gethostname()
        self.pid = os.getpid()

        # seed random for rate calculations
        random.seed()

    def setup(self, stream, encoder, hmc, logger='', severity=6, disabled_timers=None,
              filters=None):
        """Setup the HekaClient

        :param logger: Default `logger` value for all sent messages.
        :param severity: Default `severity` value for all sent
                         messages.
        :param disabled_timers: Sequence of string tokens identifying
                                timers that should be deactivated.
        :param filters: A sequence of filter callables.

        """
        from heka.path import resolve_name
        if isinstance(stream, basestring):
            stream = resolve_name(stream)()
        self.stream = stream

        if isinstance(encoder, basestring):
            encoder = resolve_name(encoder)
        self.encoder = encoder(hmc)

        self.logger = logger
        self.severity = severity

        if disabled_timers is None:
            self._disabled_timers = set()
        elif isinstance(disabled_timers, types.StringTypes):
            self._disabled_timers = set([disabled_timers])
        else:
            self._disabled_timers = set(disabled_timers)
        if filters is None:
            filters = list()
        self.filters = filters

    @property
    def is_active(self):
        # Is this client ready to transmit messages? For now we assume
        # that if a stream is set, we're good to go.
        return self.stream is not None

    def send_message(self, msg):
        # Apply any filters and, if required, pass message along to the
        # sender for delivery.
        for filter_fn in self.filters:
            if not filter_fn(msg):
                return
        try:
            data = self.encoder.encode(msg)
            self.stream.write(data)
            self.stream.flush()
        except StandardError, e:
            unicode_msg = unicode(str(msg), errors='ignore')

            err_msg = "Error sending message (%s): [%s]" % \
                      (repr(e), unicode_msg.encode("utf8"))
            sys.stderr.write(err_msg)
            return

    def add_method(self, method, override=False):
        """Add a custom method to the HekaClient instance.

        :param method: Callable that will be used as the method.
        :param override: Set this to the method name you want to
                         override. False indicates no override will
                         occur.

        """
        assert isinstance(method, types.FunctionType)

        # Obtain the heka name directly from the method
        name = method.heka_name
        if isinstance(override, basestring):
            name = override

        if override is False and hasattr(self, name):
            msg = "The name [%s] is already in use" % name
            raise SyntaxError(msg)

        self._dynamic_methods[name] = method
        meth = types.MethodType(method, self, self.__class__)
        setattr(self, name, meth)

    def heka(self, type, logger=None, severity=None, payload='',
             fields=None, timestamp=None):
        """Create a single message and pass it to the sender for
        delivery.

        :param type: String token identifying the type of message
                     payload.
        :param logger: String token identifying the message generator.
        :param severity: Numerical code (0-7) for msg severity, per RFC
                         5424.
        :param payload: Actual message contents.
        :param fields: Arbitrary key/value pairs for add'l metadata.
        :param timestamp: Custom timestamp for the message. If no timestamp
                          is given, then current time will be used.

        """
        logger = logger if logger is not None else self.logger
        severity = severity if severity is not None else self.severity
        fields = fields if fields is not None else dict()
        timestamp = time.mktime(timestamp.timetuple()) \
            if isinstance(timestamp, datetime.datetime) else timestamp

        msg = Message()
        msg.timestamp = int((timestamp or time.time()) * 1000000000)
        msg.type = type
        msg.logger = logger
        msg.severity = severity
        msg.payload = payload
        msg.env_version = self.env_version
        msg.pid = self.pid
        msg.hostname = self.hostname
        self._flatten_fields(msg, fields)

        msg.uuid = uuid.uuid5(uuid.NAMESPACE_OID, str(msg)).bytes

        self.send_message(msg)


    def timer(self, name, logger=None, severity=None, fields=None, rate=1.0):
        """Return a timer object that can be used as a context manager
        or a decorator, generating a heka 'timer' message upon exit.

        :param name: Required string label for the timer.
        :param logger: String token identifying the message generator.
        :param severity: Numerical code (0-7) for msg severity, per RFC
                         5424.
        :param fields: Arbitrary key/value pairs for add'l metadata.
        :param rate: Sample rate, btn 0 & 1, inclusive (i.e. .5 = 50%).
                     Sample rate is enforced in this method, i.e. if a
                     sample rate is used then some percentage of the
                     timers will do nothing.

        """
        # check if timer(s) is(are) disabled or if we exclude for sample rate
        if ((self._disabled_timers.intersection(set(['*', name]))) or
            (rate < 1.0 and random.random() >= rate)):
            return self._noop_timer
        msg_data = dict(logger=logger, severity=severity, fields=fields,
                        rate=rate)
        if name in self._timer_obs:
            timer = self._timer_obs[name]
            timer.msg_data = msg_data
        else:
            timer = _Timer(self, name, msg_data)
            self._timer_obs[name] = timer
        return timer

    def timer_send(self, name, elapsed, logger=None, severity=None,
                   fields=None, rate=1.0):
        """Converts timing data into a heka message for delivery.

        :param name: Required string label for the timer.
        :param elapsed: Elapsed time of the timed event, in ms.
        :param logger: String token identifying the message generator.
        :param severity: Numerical code (0-7) for msg severity, per RFC
                         5424.
        :param fields: Arbitrary key/value pairs for add'l metadata.
        :param rate: Sample rate, btn 0 & 1, inclusive (i.e. .5 = 50%).
                     Sample rate is *NOT* enforced in this method, i.e.
                     all messages will be sent through to heka, sample
                     rate is purely informational at this point.

        """
        payload = str(elapsed)
        fields = fields if fields is not None else dict()
        fields.update({'name': name, 'rate': rate})
        self.heka('timer', logger, severity, payload, fields)

    def incr(self, name, count=1, logger=None, severity=None, fields=None,
             rate=1.0):
        """Sends an 'increment counter' message.

        :param name: String label for the counter.
        :param count: Integer amount by which to increment the counter.
        :param logger: String token identifying the message generator.
        :param severity: Numerical code (0-7) for msg severity, per RFC
                         5424.
        :param fields: Arbitrary key/value pairs for add'l metadata.

        """
        if rate < 1 and random.random() >= rate:
            return
        payload = str(count)
        fields = fields if fields is not None else dict()
        fields['name'] = name
        fields['rate'] = rate
        self.heka('counter', logger, severity, payload, fields)

    # Standard Python logging API emulation
    def _oldstyle(self, severity, msg, *args, **kwargs):
        """Do any necessary string formatting and then generate the
        msg

        """
        # if `args` is a mapping then extract it
        if (len(args) == 1 and hasattr(args[0], 'keys')
            and hasattr(args[0], '__getitem__')):
            args = args[0]
        if args:
            msg = msg % args
        exc_info = kwargs.get('exc_info', False)
        if exc_info:
            if not isinstance(exc_info, tuple):
                exc_info = sys.exc_info()
            tb_lines = traceback.format_exception(exc_info[0], exc_info[1],
                                                  exc_info[2])
            s = ''.join(tb_lines)
            if s[-1:] == '\n':
                s = s[:-1]
            if msg[-1:] != '\n':
                msg = msg + '\n'
            try:
                msg = msg + s
            except UnicodeError:
                msg = msg + s.decode(sys.getfilesystemencoding())
        self.heka(type='oldstyle', severity=severity, payload=msg)

    def debug(self, msg, *args, **kwargs):
        """Log a DEBUG level message"""
        self._oldstyle(SEVERITY.DEBUG, msg, *args, **kwargs)

    def info(self, msg, *args, **kwargs):
        """Log an INFO level message"""
        self._oldstyle(SEVERITY.INFORMATIONAL, msg, *args, **kwargs)

    def warn(self, msg, *args, **kwargs):
        """Log a WARN level message"""
        self._oldstyle(SEVERITY.WARNING, msg, *args, **kwargs)

    def error(self, msg, *args, **kwargs):
        """Log an ERROR level message"""
        self._oldstyle(SEVERITY.ERROR, msg, *args, **kwargs)

    def exception(self, msg, exc_info=True, *args, **kwargs):
        """Log an ALERT level message"""
        self._oldstyle(SEVERITY.ALERT, msg, exc_info=exc_info, *args, **kwargs)

    def critical(self, msg, *args, **kwargs):
        """Log a CRITICAL level message"""
        self._oldstyle(SEVERITY.CRITICAL, msg, *args, **kwargs)

    def _flatten_fields(self, msg, field_map, prefix=None):
        for k, v in field_map.items():
            f = msg.fields.add()

            if prefix:
                full_name = "%s.%s" % (prefix, k)
            else:
                full_name = k
            f.name = full_name
            f.representation = ""

            if v is None:
                raise ValueError("None is not allowed for field values.  [%s]" % full_name)
            elif isinstance(v, types.IntType):
                f.value_type = Field.INTEGER
                f.value_integer.append(v)
            elif isinstance(v, types.FloatType):
                f.value_type = Field.DOUBLE
                f.value_double.append(v)
            elif isinstance(v, types.BooleanType):
                f.value_type = Field.BOOL
                f.value_bool.append(bool(v))
            elif isinstance(v, basestring):
                f.value_type = Field.STRING
                f.value_string.append(v)
            elif isinstance(v, types.DictType):
                msg.fields.remove(f)
                self._flatten_fields(msg, v, prefix=full_name)
            else:
                raise ValueError("Unexpected value type : [%s][%s]" % (type(v), v))
