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
#   Victor Ng (vng@mozilla.com)
#
# ***** END LICENSE BLOCK *****
from heka.client import SEVERITY
from heka.senders.udp import UdpSender
from heka.senders.dev import StdOutSender
from heka.senders.logging import StdLibLoggingSender
from mock import patch
from nose.tools import eq_, raises

import sys
import json
import logging
import StringIO


def formatter(msg):
    output = []
    for key, value in msg.items():
        output.append('%s;;;%s' % (str(key), str(value)))
    return '\n'.join(output)


@patch('sys.stdout')
class TestStdOutSender(object):
    def _make_one(self, formatter=None):
        return StdOutSender(formatter=formatter)

    def setUp(self):
        self.msg = {'this': 'is',
                    'a': 'test',
                    'payload': 'PAYLOAD'}

    def test_default_formatter(self, mock_stdout):
        sender = self._make_one()
        sender.send_message(self.msg)
        eq_(mock_stdout.write.call_count, 1)
        eq_(mock_stdout.flush.call_count, 1)
        write_args = mock_stdout.write.call_args
        eq_(json.loads(write_args[0][0]), self.msg)

    def test_custom_formatter(self, mock_stdout):
        sender = self._make_one(formatter=formatter)
        sender.send_message(self.msg)
        eq_(mock_stdout.write.call_count, 1)
        eq_(mock_stdout.flush.call_count, 1)
        mock_stdout.write.assert_called_with(formatter(self.msg) + '\n')

    def test_custom_formatter_dotted(self, mock_stdout):
        dotted = 'heka.tests.test_senders.formatter'
        sender = self._make_one(formatter=dotted)
        sender.send_message(self.msg)
        eq_(mock_stdout.write.call_count, 1)
        eq_(mock_stdout.flush.call_count, 1)
        mock_stdout.write.assert_called_with(formatter(self.msg) + '\n')


@patch('heka.senders.logging.logging')
class TestLoggingSender(object):
    msgs = [{'type': 'oldstyle', 'payload': 'oldstyle',
             'severity': SEVERITY.WARNING},
            {'type': 'this', 'payload': 'this', 'severity': SEVERITY.ERROR},
            {'type': 'that', 'payload': 'that',
             'severity': SEVERITY.INFORMATIONAL},
            {'type': 'the other', 'payload': 'the other',
             'severity': SEVERITY.DEBUG},
            ]

    def _make_one(self, *args, **kwargs):
        return StdLibLoggingSender(*args, **kwargs)

    def _send_em(self, sender):
        for msg in self.msgs:
            sender.send_message(msg)

    def test_defaults(self, mock_logging):
        sender = self._make_one()
        self._send_em(sender)
        log = mock_logging.getLogger().log
        eq_(log.call_count, 4)
        log.assert_any_call(logging.WARN, 'oldstyle')
        log.assert_any_call(logging.ERROR, json.dumps(self.msgs[1]))
        log.assert_any_call(logging.INFO, json.dumps(self.msgs[2]))
        log.assert_called_with(logging.DEBUG, json.dumps(self.msgs[3]))

    def test_alternate_logger_name(self, mock_logging):
        name = 'logger_name'
        sender = self._make_one(name)
        self._send_em(sender)
        log = mock_logging.getLogger(name).log
        eq_(log.call_count, 4)
        log.assert_any_call(logging.WARN, 'oldstyle')
        log.assert_any_call(logging.ERROR, json.dumps(self.msgs[1]))
        log.assert_any_call(logging.INFO, json.dumps(self.msgs[2]))
        log.assert_called_with(logging.DEBUG, json.dumps(self.msgs[3]))

    def test_specific_types(self, mock_logging):
        sender = self._make_one(payload_types=['this', 'that'],
                                json_types=['the other'])
        self._send_em(sender)
        log = mock_logging.getLogger().log
        eq_(log.call_count, 3)
        log.assert_any_call(logging.ERROR, 'this')
        log.assert_any_call(logging.INFO, 'that')
        log.assert_called_with(logging.DEBUG, json.dumps(self.msgs[3]))

    def test_payload_all(self, mock_logging):
        sender = self._make_one(payload_types=['*'])
        self._send_em(sender)
        log = mock_logging.getLogger().log
        eq_(log.call_count, 4)
        log.assert_any_call(logging.WARN, 'oldstyle')
        log.assert_any_call(logging.ERROR, 'this')
        log.assert_any_call(logging.INFO, 'that')
        log.assert_any_call(logging.DEBUG, 'the other')


class TestUdpSender(object):
    def _make_one(self, host, port):
        return UdpSender(host=host, port=port)

    def _init_sender(self, host='127.0.0.1', port=5565):
        self.sender = self._make_one(host, port)
        self.socket_patcher = patch.object(self.sender, 'socket')
        self.mock_socket = self.socket_patcher.start()
        self.msg = {'this': 'is',
                    'a': 'test',
                    'payload': 'PAYLOAD'}

    def tearDown(self):
        self.socket_patcher.stop()

    def test_sender(self):
        self._init_sender()
        self.sender.send_message(self.msg)
        eq_(self.mock_socket.sendto.call_count, 1)
        write_args = self.mock_socket.sendto.call_args
        eq_(json.loads(write_args[0][0]), self.msg)
        eq_(write_args[0][1], ('127.0.0.1', 5565))

    def test_sender_multiple(self):
        hosts = ['127.0.0.1', '127.0.0.2']
        ports = [5565, 5566]
        self._init_sender(host=hosts, port=ports)
        self.sender.send_message(self.msg)
        eq_(self.mock_socket.sendto.call_count, 2)
        write_args = self.mock_socket.sendto.call_args_list
        eq_(json.loads(write_args[0][0][0]), self.msg)
        eq_(write_args[0][0][1], (hosts[0], ports[0]))
        eq_(json.loads(write_args[1][0][0]), self.msg)
        eq_(write_args[1][0][1], (hosts[1], ports[1]))

    def test_sender_multiple_fewer_ports(self):
        hosts = ['127.0.0.1', '127.0.0.2']
        port = 5565
        self._init_sender(host=hosts, port=port)
        self.sender.send_message(self.msg)
        eq_(self.mock_socket.sendto.call_count, 2)
        write_args = self.mock_socket.sendto.call_args_list
        eq_(json.loads(write_args[0][0][0]), self.msg)
        eq_(write_args[0][0][1], (hosts[0], port))
        eq_(json.loads(write_args[1][0][0]), self.msg)
        eq_(write_args[1][0][1], (hosts[1], port))


class TestUDPUnicode(object):
    def setup(self):
        self._init_sender()
        self.old_stderr = sys.stderr
        sys.stderr = StringIO.StringIO()

    def _make_one(self, host, port):
        return UdpSender(host=host, port=port)

    def _init_sender(self, host='127.0.0.1', port=5565):
        self.sender = self._make_one(host, port)
        self.socket_patcher = patch.object(self.sender, 'socket')
        self.mock_socket = self.socket_patcher.start()

    def tearDown(self):
        self.socket_patcher.stop()
        sys.stderr = self.old_stderr

    @raises(UnicodeError)
    def test_bad_bytes(self):
        msg = "\xfa121a1"
        self.sender.send_message(msg)

    @raises(UnicodeError)
    def test_bad_struct(self):
        msg = {'this': 'is',
                    'a': 'test',
                    'payload': "\xfa121a1"}
        self.sender.send_message(msg)

    @raises(UnicodeError)
    def test_mixed_bad_bytes(self):
        msg = u"\u30c0".encode('utf8') + "\xfa121a1" + u"\u30c1".encode('utf8')
        self.sender.send_message(msg)

    @raises(UnicodeError)
    def test_mixed_bad_byte_struct(self):
        bad_bytes = u"\u30c0".encode('utf8') + \
                "\xfa121a1" + \
                u"\u30c1".encode('utf8')
        msg = {'this': 'is',
                    'a': 'test',
                    'payload': bad_bytes}
        self.sender.send_message(msg)

    def test_japanese(self):
        msg = u"\u30c0\u30c1\u30c2"
        self.sender.send_message(msg)
        sys.stderr.seek(0)
        err = sys.stderr.read()
        eq_(err, '')

        eq_(self.mock_socket.sendto.call_count, 1)
        write_args = self.mock_socket.sendto.call_args_list
        eq_(json.loads(write_args[0][0][0]), msg)

    def test_japanese_utf8(self):
        msg = u"\u30c0\u30c1\u30c2".encode('utf8')
        self.sender.send_message(msg)
        sys.stderr.seek(0)
        err = sys.stderr.read()
        eq_(err, '')

        eq_(self.mock_socket.sendto.call_count, 1)
        write_args = self.mock_socket.sendto.call_args_list

        # JSON serialization will encode UTF8 or real unicode strings
        # the same way, so on deserialization, you will always get
        # actual unicode strings
        eq_(json.loads(write_args[0][0][0]), msg.decode('utf8'))

    def test_japanese_struct(self):
        msg = {'this': 'is',
                    'a': 'test',
                    'payload': u"\u30c0\u30c1\u30c2"}

        self.sender.send_message(msg)
        sys.stderr.seek(0)
        err = sys.stderr.read()
        eq_(err, '')

        eq_(self.mock_socket.sendto.call_count, 1)
        write_args = self.mock_socket.sendto.call_args_list
        eq_(json.loads(write_args[0][0][0]), msg)

    def test_japanese_struct_utf8(self):
        msg = {'this': 'is',
                    'a': 'test',
                    'payload': u"\u30c0\u30c1\u30c2".encode("utf8")}
        self.sender.send_message(msg)
        sys.stderr.seek(0)
        err = sys.stderr.read()
        eq_('', err)

    def test_bug_73442(self):
        """
        This reuses actual data which caused bug 73442
        """
        msg = u'bukan\xfdrka'

        self.sender.send_message(msg)
        sys.stderr.seek(0)
        err = sys.stderr.read()
        eq_(err, '')

        eq_(self.mock_socket.sendto.call_count, 1)
        write_args = self.mock_socket.sendto.call_args_list
        eq_(json.loads(write_args[0][0][0]), msg)

    def test_bug_73442_long_msg(self):
        msg = u'bukan\xfdrka'
        self.sender.send_message(u"User (%s)" % msg)
        sys.stderr.seek(0)
        err = sys.stderr.read()
        eq_(err, '')
        eq_(self.mock_socket.sendto.call_count, 1)
        write_args = self.mock_socket.sendto.call_args_list
        eq_(json.loads(write_args[0][0][0]), u"User (%s)" % msg)
