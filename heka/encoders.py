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

from hashlib import sha1, md5

from heka.message import Message, Header, Field
from heka.message import UNIT_SEPARATOR, RECORD_SEPARATOR
from heka.message import MAX_HEADER_SIZE
from heka.message import InvalidMessage

from heka.util import json
from struct import pack
import hmac
import types
import base64

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


class MessageEncoder(json.JSONEncoder):
    """ Encode the ProtocolBuffer Message into JSON """
    def default(self, obj):
        """ Return a JSON serializable version of obj """
        if isinstance(obj, Message):
            result = {}
            for k, v in obj._fields.items():
                if k.name == 'fields':
                    result[k.name] = [self.default(x) for x in v]
                elif k.name == 'uuid':
                    result[k.name] = base64.b64encode(v)
                else:
                    result[k.name] = v
            return result
        elif isinstance(obj, Field):
            tmp = {"name": obj.name,
                   "value_type": PB_TYPEMAP[obj.value_type],
                   "value_format": "RAW"}
            key_name = "value_%s" % tmp['value_type'].lower()
            tmp[key_name] = [x for x in getattr(obj, key_name)]
            return tmp

        return json.JSONEncoder.default(self, obj)


class JSONEncoder(object):

    def __init__(self, hmc=None):
        self.hmc = hmc

    def msg_to_payload(self, msg):
        data = json.dumps(msg, cls=MessageEncoder)
        return data

    def encode(self, msg):
        if not isinstance(msg, Message):
            raise RuntimeError('You must encode only Message objects')

        payload = self.msg_to_payload(msg)

        h = Header()
        h.message_encoding = Header.MessageEncoding.Value('JSON')
        h.message_length = len(payload)

        if self.hmc:
            compute_hmac(h, self.hmc, payload)

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

        # TODO: what do we want to do with message > MAX_MESSAGE_SIZE?
        # Sentry stacktraces may sometimes blow this up
        return byte_data

    def _json_to_message(self, json_data):
        if isinstance(json_data, dict) and 'uuid' in json_data:
            msg = Message()
            msg.uuid = base64.b64decode(str(json_data['uuid']))
            msg.timestamp = json_data['timestamp']
            msg.type = json_data['type']
            msg.logger = json_data['logger']
            msg.severity = json_data['severity']
            msg.payload = json_data['payload']
            msg.env_version = json_data['env_version']
            msg.pid = json_data.get('pid', '0')
            msg.hostname = json_data.get('hostname', '""')

            for field_dict in json_data.get('fields', []):
                f = msg.fields.add()
                f.value_type = PB_NAMETYPE_TO_INT[field_dict['value_type']]

                # Everything is raw
                f.value_format = 0
                del field_dict['value_type']
                del field_dict['value_format']

                for k, v in field_dict.items():
                    cls_name = getattr(f, k).__class__.__name__
                    if cls_name == 'RepeatedScalarFieldContainer':
                        for v1 in v:
                            getattr(f, k).append(v1)
                    else:
                        setattr(f, k, v)
            return msg
        return json_data

    def decode(self, bytes):
        obj = json.loads(bytes, object_hook=self._json_to_message)
        return obj


def compute_hmac(header, hmc, payload):
    header.hmac_signer = hmc['signer']
    header.hmac_key_version = hmc['key_version']
    header.hmac_hash_function = HmacHashFunc.Value(hmc['hash_function'])
    hash_func = HASHNAME_TO_FUNC[hmc['hash_function']]
    header.hmac = hmac.new(hmc['key'], payload, hash_func).digest()


class ProtobufEncoder(object):

    def __init__(self, hmc=None):
        self.hmc = hmc

    def msg_to_payload(self, msg):
        return msg.SerializeToString()

    def encode(self, msg):
        if not isinstance(msg, Message):
            raise RuntimeError('You must encode only Message objects')

        payload = self.msg_to_payload(msg)

        h = Header()
        h.message_encoding = Header.MessageEncoding.Value('PROTOCOL_BUFFER')
        h.message_length = len(payload)

        if self.hmc:
            compute_hmac(h, self.hmc, payload)

        header_data = h.SerializeToString()
        header_size = len(header_data)
        pack_fmt = "!bb%dsb%ds" % (header_size, len(payload))
        byte_data = pack(pack_fmt,
                         RECORD_SEPARATOR,
                         header_size,
                         header_data,
                         UNIT_SEPARATOR,
                         payload)
        return byte_data

    def decode(self, bytes):
        msg = Message()
        msg.ParseFromString(bytes)
        return msg


ENCODERS = {Header.MessageEncoding.Value('PROTOCOL_BUFFER'): ProtobufEncoder(),
            Header.MessageEncoding.Value('JSON'): JSONEncoder()}


def decode_message(bytes):
    """
    return header and message object
    """
    header_len = ord(bytes[1])
    header_bytes = bytes[2:2+header_len]

    # Now double check the header
    h = Header()
    h.ParseFromString(header_bytes)
    encoder = ENCODERS[h.message_encoding]
    return h, encoder.decode(bytes[header_len+3:])


def nest_field_data(fields, prefix=None):
    result = {}

    for f in fields:
        realname = f.name

        if f.value_type == Field.INTEGER:
            result[realname] = f.value_integer[0]
        elif f.value_type == Field.DOUBLE:
            result[realname] = f.value_double[0]
        elif f.value_type == Field.BOOL:
            result[realname] = f.value_bool[0]
        elif f.value_type == Field.STRING:
            result[realname] = f.value_string[0]
        else:
            raise RuntimeError("Unexpected field type: %s" % str(f))

    # TODO: do a one time pass to 'fix' any dot notation stuff
    for k, v in result.items():
        terms = k.split(".")

        if len(terms) == 1:
            continue

        del result[k]

        obj = result
        for segment in terms[:-1]:
            if segment not in obj:
                obj[segment] = {}
            obj = obj[segment]

        if terms[-1] not in obj:
            obj[terms[-1]] = v
        else:
            if isinstance(obj[terms[-1]], types.ListType):
                obj[terms[-1]].append(v)
            else:
                obj[terms[-1]] = [obj[terms[-1]], v]

    return result
