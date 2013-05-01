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

from heka.message_pb2 import Message, Field, Header  # NOQA

MAX_HEADER_SIZE = 255
MAX_MESSAGE_SIZE = 64 * 1024
RECORD_SEPARATOR = 0x1e
UNIT_SEPARATOR = 0x1f
UUID_SIZE = 16


class InvalidMessage(StandardError):
    pass


def first_value(msg, name):
    """
    Decode the first field where the name matches
    """
    matching_fields = [f for f in msg.fields if f.name == name]
    if matching_fields:
        from heka.encoders import PB_FIELDMAP
        f = matching_fields[0]
        return getattr(f, PB_FIELDMAP[f.value_type])[0]
    return None
