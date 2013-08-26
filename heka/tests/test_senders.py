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
from datetime import datetime
from heka.client import HekaClient
from heka.tests.helpers import decode_message
from heka.message import Message
from heka.config import build_sender
from nose.tools import eq_
import time
import uuid


class encoder(object):
    def encode(self, msg):
        output = []
        for key, value in msg.items():
            output.append('%s;;;%s' % (str(key), str(value)))
        return '\n'.join(output)


class TestWrappedSender(object):
    def _make_one(self):
        encoder = 'heka.encoders.JSONEncoder'
        return build_sender('heka.streams.DebugCaptureStream', encoder)

    def setUp(self):

        msg = Message()
        msg.timestamp = int(time.time() * 1000000)
        msg.type = 'sentry'
        msg.logger = ''
        msg.severity = 3
        msg.payload = 'some_data'
        msg.env_version = '0.8'
        msg.pid = 55
        msg.hostname = 'localhost'
        client = HekaClient(None, None)
        client._flatten_fields(msg, {'foo': 'bar',
                               'blah': 42,
                               'cef_meta': {'syslog_name': 'some-syslog-thing',
                            'syslog_level': 5}})

        msg.uuid = str(uuid.uuid5(uuid.NAMESPACE_OID, str(msg)))

        self.msg =  msg


    def _extract_full_msg(self, bytes):
        h, m = decode_message(bytes)
        return m

    def test_default_encoder(self):
        sender = self._make_one()
        sender.send_message(self.msg)
        eq_(len(sender.stream.msgs), 1)

        msg = self._extract_full_msg(sender.stream.msgs[0])
        eq_(msg, self.msg)
