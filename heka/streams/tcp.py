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
#   Victor Ng (vng@mozilla.com)
#
# ***** END LICENSE BLOCK *****

from __future__ import absolute_import

# For TCP
from types import StringTypes
import threading
import socket

"""
This is a simple TCP stream.  You don't want to use this for
anything in production as we don't handle connection failure,
reconnection, stalled sockets or any kind of failure scenario
whatsoever.

It is however useful for debugging.
"""


class TcpStream(object):
    """Sends heka messages out via a TCP socket."""
    def __init__(self, host, port):
        """Create TcpStream object.

        :param host: A string or sequence of strings representing the
                     hosts to which messages should be delivered.
        :param port: An integer or sequence of integers representing
                     the ports to which the messages should be
                     delivered. Will be zipped w/ the provided hosts to
                     generate host/port pairs. If there are extra
                     hosts, the last port in the sequence will be
                     repeated for each extra host. If there are extra
                     ports they will be truncated and ignored.

        """
        if isinstance(host, StringTypes):
            host = [host]
        if isinstance(port, int):
            port = [port]
        num_extra_hosts = len(host) - len(port)
        if num_extra_hosts > 0:
            port.extend(num_extra_hosts * [port[-1]])
        self._destinations = zip(host, port)

        self.sockets = [socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                        for d in self._destinations]

        self._started = False
        self._lock = threading.RLock()

    def write(self, data):
        """Send bytes off to the heka listener(s).

        :param data: bytes to send to the listener

        """
        with self._lock:
            # Lazy connect the sockets on first write
            if not self._started:
                for (sock, (host, port)) in zip(self.sockets, self._destinations):
                    sock.connect((host, port))
                self._started = True

        for sock in self.sockets:
            sock.sendall(data)

    def flush(self):
        pass
