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
from heka.streams.udp import UdpStream
from heka.streams.tcp import TcpStream
from mock import patch, Mock
from nose.tools import eq_

import json


class TestUdpStream(object):
    def _make_one(self, host, port):
        return UdpStream(host=host, port=port)

    def _init_sender(self, host='127.0.0.1', port=5565):

        self.stream = self._make_one(host, port)
        self.socket_patcher = patch.object(self.stream, 'socket')
        self.mock_socket = self.socket_patcher.start()

        self.msg = json.dumps({'this': 'is', 'a': 'test', 'payload':
                               'PAYLOAD'})

    def tearDown(self):
        self.socket_patcher.stop()

    def test_sender(self):
        self._init_sender()
        self.stream.write(self.msg)
        eq_(self.mock_socket.sendto.call_count, 1)
        write_args = self.mock_socket.sendto.call_args
        eq_(write_args[0][0], self.msg)
        eq_(write_args[0][1], ('127.0.0.1', 5565))

    def test_sender_multiple(self):
        hosts = ['127.0.0.1', '127.0.0.2']
        ports = [5565, 5566]
        self._init_sender(host=hosts, port=ports)
        self.stream.write(self.msg)
        eq_(self.mock_socket.sendto.call_count, 2)
        write_args = self.mock_socket.sendto.call_args_list
        eq_(write_args[0][0][0], self.msg)
        eq_(write_args[0][0][1], (hosts[0], ports[0]))
        eq_(write_args[1][0][0], self.msg)
        eq_(write_args[1][0][1], (hosts[1], ports[1]))

    def test_sender_multiple_fewer_ports(self):
        hosts = ['127.0.0.1', '127.0.0.2']
        port = 5565
        self._init_sender(host=hosts, port=port)
        self.stream.write(self.msg)
        eq_(self.mock_socket.sendto.call_count, 2)
        write_args = self.mock_socket.sendto.call_args_list
        eq_(write_args[0][0][0], self.msg)
        eq_(write_args[0][0][1], (hosts[0], port))
        eq_(write_args[1][0][0], self.msg)
        eq_(write_args[1][0][1], (hosts[1], port))
