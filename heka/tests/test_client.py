# -*- coding: utf-8 -*-

# ***** BEGIN LICENSE BLOCK *****
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this file,
# You can obtain one at http://mozilla.org/MPL/2.0/.

# The Initial Developer of the Original Code is the Mozilla Foundation.
# Portions created by the Initial Developer are Copyright (C) 2012
# the Initial Developer. All Rights Reserved.
#
# Contributor(s):
#   Rob Miller (rmiller@mozilla.com)
#
# ***** END LICENSE BLOCK *****
from __future__ import absolute_import
from heka.client import HekaClient, SEVERITY
from heka.encoders import StdlibPayloadEncoder, ProtobufEncoder
from heka.encoders import UNIT_SEPARATOR, RECORD_SEPARATOR
from heka.holder import get_client
from heka.holder import get_client
from heka.logging import SEVERITY_MAP
from heka.message import Message, Header, Field
from heka.message import first_value
from heka.message import first_value
from heka.streams import DebugCaptureStream
from heka.streams import StdLibLoggingStream
from heka.tests.helpers import decode_message
from heka.tests.helpers import decode_message, dict_to_msg
from mock import Mock
from mock import patch
from nose.tools import eq_, ok_
from nose.tools import raises
import StringIO
import datetime
import logging
import os
import socket
import sys
import threading
import time

try:
    import simplejson as json
except:
    import json  # NOQA



class TestHekaClient(object):
    logger = 'tests'
    timer_name = 'test'

    def setUp(self):
        self.mock_stream = DebugCaptureStream()
        class NoEncoder(object):
            def __init__(self, hmc):
                pass
            def encode(self, msg):
                return msg
        self.client = HekaClient(self.mock_stream, self.logger,
                encoder=NoEncoder)
        # overwrite the class-wide threadlocal w/ an instance one
        # so values won't persist btn tests
        self.timer_ob = self.client.timer(self.timer_name)
        self.timer_ob.__dict__['_local'] = threading.local()

    def tearDown(self):
        del self.timer_ob.__dict__['_local']
        del self.mock_stream

    def _extract_full_msg(self):
        msg = self.mock_stream.msgs.pop()
        return msg

    def compute_timestamp(self):
        """
        These should be nanoseconds 
        """
        return int(time.time() * 1000000000)

    @raises(ValueError)
    def test_heka_flatten_nulls(self):
        """
        None values in the fields dictionary should throw an error
        """
        payload = 'this is a test'
        self.client.heka('some_msg_type', payload=payload, fields={'foo': None})

    def test_heka_bare(self):
        payload = 'this is a test'

        before = self.compute_timestamp()

        msgtype = 'testtype'
        self.client.heka(msgtype, payload=payload)
        after = self.compute_timestamp()

        full_msg = self._extract_full_msg()
        # check the payload
        eq_(full_msg.payload, payload)
        # check the various default values
        ok_(before < full_msg.timestamp < after)
        eq_(full_msg.type, msgtype)
        eq_(full_msg.severity, self.client.severity)
        eq_(full_msg.logger, self.logger)
        eq_(full_msg.pid, os.getpid())
        eq_(full_msg.hostname, socket.gethostname())
        eq_(full_msg.env_version, self.client.env_version)

    def test_heka_full(self):
        heka_args = dict(payload='this is another test',
                         logger='alternate',
                         severity=2,
                         fields={'foo': 'bar',
                                 'boo': 'far'})
        msgtype = 'bawlp'
        self.client.heka(msgtype, **heka_args)
        actual_msg = self._extract_full_msg()

        heka_args.update({'type': msgtype,
                          'env_version': self.client.env_version,
                          'heka_pid': os.getpid(),
                          'heka_hostname': socket.gethostname(),
                          'timestamp': actual_msg.timestamp})

        # Everything but the UUID should be identical
        expected_msg = dict_to_msg(heka_args)

        pbencoder = ProtobufEncoder()
        h, actual_msg = decode_message(pbencoder.encode(actual_msg))
        h, expected_msg = decode_message(pbencoder.encode(expected_msg))

        expected_msg.uuid = ''
        actual_msg.uuid = ''
        eq_(actual_msg, expected_msg)

    def test_heka_timestamp(self):
        payload = 'this is a timestamp test'

        timestamp = time.time()

        msgtype = 'testtype'
        self.client.heka(msgtype, payload=payload, timestamp=timestamp)

        full_msg = self._extract_full_msg()

        eq_(full_msg.timestamp, timestamp * 1000000000)

        timestamp = datetime.datetime.now()
        self.client.heka(msgtype, payload=payload, timestamp=timestamp)

        full_msg = self._extract_full_msg()

        eq_(full_msg.timestamp, time.mktime(timestamp.timetuple()) * 1000000000)

    def test_oldstyle(self):
        payload = 'debug message'
        self.client.debug(payload)
        full_msg = self._extract_full_msg()
        eq_(full_msg.payload, payload)
        eq_(full_msg.severity, SEVERITY.DEBUG)

    def test_oldstyle_args(self):
        payload = '1, 2: %s\n3, 4: %s'
        args = ('buckle my shoe', 'shut the door')
        self.client.warn(payload, *args)
        full_msg = self._extract_full_msg()
        eq_(full_msg.payload, payload % args)

    def test_oldstyle_mapping_arg(self):
        payload = '1, 2: %(onetwo)s\n3, 4: %(threefour)s'
        args = {'onetwo': 'buckle my shoe',
                'threefour': 'shut the door'}
        self.client.warn(payload, args)
        full_msg = self._extract_full_msg()
        eq_(full_msg.payload, payload % args)

    def test_oldstyle_exc_info(self):
        payload = 'traceback ahead -->'
        try:
            a = b  # NOQA
        except NameError:
            self.client.error(payload, exc_info=True)
        full_msg = self._extract_full_msg()
        ok_(full_msg.payload.startswith(payload))
        ok_("NameError: global name 'b' is not defined" in full_msg.payload)
        ok_('test_client.py' in full_msg.payload)

    def test_oldstyle_exc_info_auto(self):
        payload = 'traceback ahead -->'
        try:
            a = b  # NOQA
        except NameError:
            self.client.exception(payload)
        full_msg = self._extract_full_msg()
        ok_(full_msg.payload.startswith(payload))
        ok_("NameError: global name 'b' is not defined" in full_msg.payload)
        ok_('test_client.py' in full_msg.payload)

    def test_oldstyle_exc_info_passed(self):
        def name_error():
            try:
                a = b  # NOQA
            except NameError:
                return sys.exc_info()

        ei = name_error()
        payload = 'traceback ahead -->'
        self.client.critical(payload, exc_info=ei)
        full_msg = self._extract_full_msg()
        ok_(full_msg.payload.startswith(payload))
        ok_("NameError: global name 'b' is not defined" in full_msg.payload)
        ok_('test_client.py' in full_msg.payload)

    def test_timer_contextmanager(self):
        name = self.timer_name
        with self.client.timer(name) as timer:
            time.sleep(0.01)

        ok_(timer.result >= 10)
        full_msg = self._extract_full_msg()
        eq_(full_msg.payload, str(timer.result))
        eq_(full_msg.type, 'timer')
        eq_(first_value(full_msg, 'name'), name)
        eq_(first_value(full_msg, 'rate'), 1)

    def test_timer_decorator(self):
        @self.client.timer(self.timer_name)
        def timed():
            time.sleep(0.01)

        ok_(not len(self.mock_stream.msgs))
        timed()
        full_msg = self._extract_full_msg()
        ok_(int(full_msg.payload) >= 10)
        eq_(full_msg.type, 'timer')
        eq_(first_value(full_msg, 'name'), self.timer_name)
        eq_(first_value(full_msg, 'rate'), 1)
        eq_(first_value(full_msg, 'rate'), 1)

    def test_timer_with_rate(self):
        name = self.timer_name

        @self.client.timer(name, rate=0.01)
        def timed():
            time.sleep(0.001)

        # leverage chance by using a large sample
        # instead of just 10 samples
        for i in range(1000):
            timed()

        # this is a weak test, but not quite sure how else to
        # test explicitly random behaviour
        ok_(len(self.mock_stream.msgs) < 200)

    def test_incr(self):
        name = 'incr'
        self.client.incr(name)

        full_msg = self._extract_full_msg()
        eq_(full_msg.type, 'counter')
        eq_(full_msg.logger, self.logger)
        eq_(first_value(full_msg, 'name'), name)

        # You have to have a rate set here
        eq_(first_value(full_msg, 'rate'), 1)
        eq_(full_msg.payload, '1')

        self.client.incr(name, 10)
        full_msg = self._extract_full_msg()
        eq_(full_msg.payload, '10')

class TestStdLogging(object):
    def test_can_use_stdlog(self):
        self.mock_stream = StdLibLoggingStream('testlogger')


        with patch.object(self.mock_stream.logger, 'log') as mock_log:
            self.client = HekaClient(self.mock_stream,
                    'my_logger_name',
                    encoder='heka.encoders.StdlibPayloadEncoder')
            self.client.heka('stdlog', payload='this is some text')
            ok_(mock_log.called)
            ok_(mock_log.call_count == 1)

            log_level, call_data = mock_log.call_args[0]
            eq_(call_data, 'stdlog: this is some text')
            eq_(log_level, logging.INFO)


class TestDisabledTimer(object):
    logger = 'tests'
    timer_name = 'test'

    def _extract_full_msg(self):
        h, m = decode_message(self.stream.msgs[0])
        return m

    def setUp(self):
        self.stream = DebugCaptureStream()
        self.client = HekaClient(self.stream, self.logger)
        # overwrite the class-wide threadlocal w/ an instance one
        # so values won't persist btn tests
        self.timer_ob = self.client.timer(self.timer_name)
        self.timer_ob.__dict__['_local'] = threading.local()

    def tearDown(self):
        self.stream.msgs.clear()
        del self.timer_ob.__dict__['_local']

    def test_timer_contextmanager(self):
        name = self.timer_name
        with self.client.timer(name) as timer:
            time.sleep(0.01)

        ok_(timer.result >= 10)
        full_msg = self._extract_full_msg()
        eq_(full_msg.payload, str(timer.result))
        eq_(full_msg.type, 'timer')

        eq_(first_value(full_msg, 'name'), self.timer_name)
        eq_(first_value(full_msg, 'rate'), 1)

        # Now disable it
        self.client._disabled_timers.add(name)
        with self.client.timer(name) as timer:
            time.sleep(0.01)
            ok_(timer.result is None)

        # Now re-enable it
        self.client._disabled_timers.remove(name)
        self.stream.msgs.clear()
        with self.client.timer(name) as timer:
            time.sleep(0.01)

        ok_(timer.result >= 10)
        full_msg = self._extract_full_msg()
        eq_(full_msg.payload, str(timer.result))
        eq_(full_msg.type, 'timer')

        eq_(first_value(full_msg, 'name'), name)
        eq_(first_value(full_msg, 'rate'), 1.0)

    def test_timer_decorator(self):
        name = self.timer_name

        @self.client.timer(name)
        def foo():
            time.sleep(0.01)
        foo()

        eq_(len(self.stream.msgs), 1)

        full_msg = self._extract_full_msg()
        ok_(int(full_msg.payload) >= 10,
            "Got: %d" % int(full_msg.payload))
        eq_(full_msg.type, 'timer')

        eq_(first_value(full_msg, 'name'), 'test')
        eq_(first_value(full_msg, 'rate'), 1)

        # Now disable it
        self.client._disabled_timers.add(name)
        self.stream.msgs.clear()

        @self.client.timer(name)
        def foo2():
            time.sleep(0.01)
        foo2()

        eq_(len(self.stream.msgs), 0)

        # Now re-enable it
        self.client._disabled_timers.remove(name)
        self.stream.msgs.clear()

        @self.client.timer(name)
        def foo3():
            time.sleep(0.01)
        foo3()

        full_msg = self._extract_full_msg()
        ok_(int(full_msg.payload) >= 10)
        eq_(full_msg.type, 'timer')

        eq_(first_value(full_msg, 'name'), 'test')
        eq_(first_value(full_msg, 'rate'), 1)

    def test_disable_all_timers(self):
        name = self.timer_name

        @self.client.timer(name)
        def foo():
            time.sleep(0.01)
        foo()

        eq_(len(self.stream.msgs), 1)

        full_msg = self._extract_full_msg()
        ok_(int(full_msg.payload) >= 10)
        eq_(full_msg.type, 'timer')

        eq_(first_value(full_msg, 'name'), 'test')
        eq_(first_value(full_msg, 'rate'), 1)

        # Now disable everything
        self.client._disabled_timers.add('*')
        self.stream.msgs.clear()

        @self.client.timer(name)
        def foo2():
            time.sleep(0.01)
        foo2()

        eq_(len(self.stream.msgs), 0)


class TestUnicode(object):
    logger = 'tests'
    timer_name = 'test'

    def setUp(self):
        self.mock_sender = Mock()
        self.mock_sender.send_message.side_effect = \
            UnicodeError("UnicodeError encoding user data")
        self.client = HekaClient(self.mock_sender, self.logger)
        # overwrite the class-wide threadlocal w/ an instance one
        # so values won't persist btn tests
        self.timer_ob = self.client.timer(self.timer_name)
        self.timer_ob.__dict__['_local'] = threading.local()

        self.old_stderr = sys.stderr
        sys.stderr = StringIO.StringIO()

    def tearDown(self):
        del self.timer_ob.__dict__['_local']
        del self.mock_sender
        sys.stderr = self.old_stderr

    def test_unicode_failure(self):
        msg = "mock will raise unicode error here"
        self.client.send_message(msg)
        sys.stderr.seek(0)
        err = sys.stderr.read()
        ok_('Error sending' in err)

class TestClientHolder(object):
    def test_get_client(self):
        heka = get_client('new_client')
        assert heka != None

    def test_get_client_with_cfg(self):
        cfg = {'logger': 'amo.dev',
               'stream': {'class': 'heka.streams.UdpStream',
                          'host': ['logstash1', 'logstash2'],
                          'port': '5566'},
               }
        heka = get_client('amo.dev', cfg)
        assert heka != None

