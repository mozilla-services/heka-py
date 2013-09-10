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
#   Victor Ng (vng@mozilla.com)
#
# ***** END LICENSE BLOCK *****
from __future__ import absolute_import

from datetime import datetime
from hashlib import sha1, md5
from heka.encoders import ProtobufEncoder
from heka.encoders import UNIT_SEPARATOR, RECORD_SEPARATOR
from heka.message import first_value, Header, Message
from heka.tests.helpers import decode_message
from heka.tests.helpers import dict_to_msg
from nose.tools import eq_
import base64
import hmac
import json
import uuid

SAMPLE_MSG = dict_to_msg({'uuid': '0123456789012345',
                          'type': 'sentry',
                          'logger': '',
                          'severity': 3,
                          'env_version': '0.8', 'heka_pid': 55,
                          'heka_hostname': 'localhost',
                          'timestamp': int(datetime.utcnow().strftime('%s')) * 1000000,
                          'payload': 'some_data', 'fields': {'foo': 'bar',
                          'blah': 42,
                          'cef_meta': {'syslog_name': 'some-syslog-thing',
                          'syslog_level': 5}}})


class TestProtobufEncoder(object):
    def test_protobuf_encoding(self):
        enc = ProtobufEncoder()

        bytes = enc.encode(SAMPLE_MSG)

        eq_(ord(bytes[0]), RECORD_SEPARATOR)
        header_len = ord(bytes[1])
        header = bytes[2:2+header_len]

        # Now double check the header
        h = Header()
        h.ParseFromString(header)

        eq_(ord(bytes[header_len+2]), UNIT_SEPARATOR)

        pb_data = bytes[header_len+3:]
        eq_(len(pb_data), h.message_length)

        msg = Message()
        msg.ParseFromString(pb_data)
        eq_(msg.uuid, SAMPLE_MSG.uuid)
        eq_(msg.timestamp, SAMPLE_MSG.timestamp)
        eq_(msg.payload, SAMPLE_MSG.payload)

        # Check the 3 fields
        eq_(len(msg.fields), 4)
        eq_(first_value(msg, 'foo'), 'bar')
        eq_(first_value(msg, 'blah'), 42)
        eq_(first_value(msg, 'cef_meta.syslog_name'), 'some-syslog-thing')
        eq_(first_value(msg, 'cef_meta.syslog_level'), 5)

    def test_hmac_signer_sha1(self):
        hmac_signer = {'signer': 'vic',
                       'key_version': 1,
                       'hash_function': 'SHA1',
                       'key': 'some_key'}

        enc = ProtobufEncoder(hmac_signer)

        payload = enc.msg_to_payload(SAMPLE_MSG)
        bytes = enc.encode(SAMPLE_MSG)
        header, message = decode_message(bytes)

        e1 = hmac.new(hmac_signer['key'], payload, sha1).digest()
        eq_(header.hmac, e1)

    def test_hmac_signer_md5(self):
        hmac_signer = {'signer': 'vic',
                       'key_version': 1,
                       'hash_function': 'MD5',
                       'key': 'some_key'}

        enc = ProtobufEncoder(hmac_signer)

        bytes = enc.encode(SAMPLE_MSG)
        header, message = decode_message(bytes)

        payload = enc.msg_to_payload(SAMPLE_MSG)
        e1 = hmac.new(hmac_signer['key'], payload, md5).digest()
        eq_(header.hmac, e1)
