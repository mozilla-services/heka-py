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
import uuid



class TestHmacMessages(object):
    def setup(self):
        self.msg = Message(uuid='0123456789012345',
                type='hmac',
                timestamp=1000000)

    def render(self, bytes, name):
        hex = ":".join("%02x" % (ord(c)) for c in bytes)
        print "\n%s [%s]" % (name, hex)
        return hex

    def test_hmac_signer_md5(self):
        hmac_signer = {'signer': 'vic',
                       'key_version': 1,
                       'hash_function': 'MD5',
                       'key': 'some_key'}

        enc = ProtobufEncoder(hmac_signer)

        bytes = enc.encode(self.msg)
        header, message = decode_message(bytes)
        self.render(header.SerializeToString(), "Header bytes")

        payload = enc.msg_to_payload(self.msg)
        e1 = hmac.new(hmac_signer['key'], payload, md5).digest()
        eq_(header.hmac, e1)
        self.render(bytes, 'Full MD5 signed message')
        self.render(header.hmac, 'md5 hmac')
