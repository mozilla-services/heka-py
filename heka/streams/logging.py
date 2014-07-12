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
"""Logging Compatibility layer

Allows heka code to generate output using Python's standard library's
`logging` module.

"""
from __future__ import absolute_import

import logging
import struct


class StdLibLoggingStream(object):
    """
    Stream that passes messages off to Python stdlib's `logging`
    module for delivery.

    The StdLibLoggingStream *must* be used with the StdlibPayloadEncoder.
    """
    def __init__(self, logger_name=None):
        """Create a StdLibLoggingStream

        :param logger_name: Name of logger that should be fetched from
                            logging module.
        """
        if logger_name is None:
            self.logger = logging.getLogger()
        else:
            self.logger = logging.getLogger(logger_name)

    def write(self, msg):
        # The first byte is always the stdlib logging severity
        # level.
        log_struct, msg_type, actual_msg = msg[0], msg[1:11].strip(), msg[11:]
        log_level = struct.unpack('B', log_struct)[0]
        self.logger.log(log_level, "%s: %s" % (msg_type, actual_msg))

    def flush(self):
        pass
