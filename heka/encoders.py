# ***** BEGIN LICENSE BLOCK *****
# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file, You can
# obtain one at http://mozilla.org/MPL/2.0/.
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

from hashlib import sha1, md5

from heka.logging import LOGLEVEL_MAP
from heka.message import Message, Header, Field
from heka.message import UNIT_SEPARATOR, RECORD_SEPARATOR
from heka.message import MAX_HEADER_SIZE
from heka.message import InvalidMessage
from heka.message import first_value

from struct import pack
import hmac
import logging


HmacHashFunc = Header.HmacHashFunction

HASHNAME_TO_FUNC = {'SHA1': sha1, 'MD5': md5}

PB_NAMETYPE_TO_INT = {'STRING': 0,
                      'BYTES': 1,
                      'INTEGER': 2,
                      'DOUBLE': 3,
                      'BOOL': 4}

PB_TYPEMAP = {0: 'STRING',
              1: 'BYTES',
              2: 'INTEGER',
              3: 'DOUBLE',
              4: 'BOOL'}

PB_FIELDMAP = {0: 'value_string',
               1: 'value_bytes',
               2: 'value_integer',
               3: 'value_double',
               4: 'value_bool'}


class NullEncoder(object):
    def __init__(self, hmc):
        pass

    def encode(self, msg):
        return msg


class BaseEncoder(object):
    def compute_hmac(self, header, hmc, payload):
        header.hmac_signer = hmc['signer']
        header.hmac_key_version = hmc['key_version']
        header.hmac_hash_function = HmacHashFunc.Value(hmc['hash_function'])
        hash_func = HASHNAME_TO_FUNC[hmc['hash_function']]
        header.hmac = hmac.new(hmc['key'], payload, hash_func).digest()

    def encode(self, msg):
        if not isinstance(msg, Message):
            raise RuntimeError('You must encode only Message objects')

        payload = self.msg_to_payload(msg)

        h = Header()
        h.message_length = len(payload)

        if self.hmc:
            self.compute_hmac(h, self.hmc, payload)

        header_data = h.SerializeToString()
        header_size = len(header_data)

        if header_size > MAX_HEADER_SIZE:
            raise InvalidMessage("Header is too long")

        pack_fmt = "!bb%dsb%ds" % (header_size, len(payload))
        byte_data = pack(pack_fmt,
                         RECORD_SEPARATOR,
                         header_size,
                         header_data,
                         UNIT_SEPARATOR,
                         payload)
        return byte_data


class StdlibPayloadEncoder(BaseEncoder):
    """
    If an incoming message does not have a 'loglevel' set,
    we just use a default of logging.INFO
    """
    def __init__(self, hmc=None):
        self.hmc = hmc

    def msg_to_payload(self, msg):
        log_level = first_value(msg, 'loglevel')
        if log_level is None:
            # Try computing it from msg.severity
            if msg.severity:
                log_level = LOGLEVEL_MAP[msg.severity]
            else:
                log_level = logging.INFO

            f = msg.fields.add()
            f.name = 'loglevel'
            f.representation = ""
            f.value_type = Field.INTEGER
            f.value_integer.append(log_level)

        data = msg.payload
        return pack('B10s', log_level, msg.type[:10] + (" "*(10-len(msg.type)))) + data

    def decode(self, bytes):
        """
        stdlib logging is a lossy encoder, you can't decode a full
        message back
        """
        raise NotImplementedError

    def encode(self, msg):
        if not isinstance(msg, Message):
            raise RuntimeError('You must encode only Message objects')
        return self.msg_to_payload(msg)


class ProtobufEncoder(BaseEncoder):

    def __init__(self, hmc=None):
        self.hmc = hmc

    def msg_to_payload(self, msg):
        return msg.SerializeToString()

    def decode(self, bytes):
        msg = Message()
        msg.ParseFromString(bytes)
        return msg
