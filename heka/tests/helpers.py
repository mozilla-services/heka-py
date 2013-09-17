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

from heka.encoders import ProtobufEncoder
from heka.message import Message, Field
from heka.message import Header
from heka.message import UUID_SIZE
from heka.message import InvalidMessage
import uuid
import time
import types


def dict_to_msg(py_data):
    """
    Encode a python dictionary into a ProtocolBuffer Message
    object.  This is only useful for testing.
    """
    msg = Message()
    msg.uuid = py_data.get('uuid', uuid.uuid5(uuid.NAMESPACE_OID,
                                              str(py_data)).bytes)
    if len(msg.uuid) != UUID_SIZE:
        raise InvalidMessage("UUID must be 16 bytes long")

    msg.timestamp = py_data.get('timestamp', int(time.time() * 1000000))
    msg.type = py_data['type']
    msg.logger = py_data['logger']
    msg.severity = py_data['severity']
    msg.payload = py_data['payload']
    msg.env_version = py_data['env_version']
    msg.pid = py_data['heka_pid']
    msg.hostname = py_data['heka_hostname']
    _flatten_fields(msg, py_data['fields'])
    return msg


def _flatten_fields(msg, field_map, prefix=None):
    for k, v in field_map.items():
        f = msg.fields.add()

        if prefix:
            full_name = "%s.%s" % (prefix, k)
        else:
            full_name = k
        f.name = full_name
        f.representation = ""

        if isinstance(v, types.IntType):
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
            _flatten_fields(msg, v, prefix=full_name)
        else:
            msg = "Unexpected value type : [%s][%s]" % (type(v), v)
            raise ValueError(msg)

def decode_message(bytes):
    """
    Decode the header and message object from raw bytes
    """
    header_len = ord(bytes[1])
    header = bytes[2:2+header_len]

    # Now double check the header
    h = Header()
    h.ParseFromString(header)

    pb_data = bytes[header_len+3:]

    msg = Message()
    msg.ParseFromString(pb_data)

    return h, msg
