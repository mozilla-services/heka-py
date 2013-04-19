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
#
# ***** END LICENSE BLOCK *****
from __future__ import absolute_import

import sys


class StdOutStream(object):
    """
    This is implemented as a class so that mocks can properly stub out
    sys.stdout
    """
    def write(self, data):
        sys.stdout.write(data)

    def flush(self):
        sys.stdout.flush()


class FileStream(object):
    """Emits messages to a filesystem file."""
    def __init__(self, filepath):
        self.filestream = open(filepath, 'a')

    def write(self, data):
        self.filestream.write(data)

    def flush(self):
        self.filestream.flush()


class DebugCaptureStream(object):
    """
    Captures up to 100 heka messages in a circular buffer for
    inspection later.

    This is only for DEBUGGING.  Do not use this for anything except
    development.

    """
    def __init__(self, **kwargs):
        import collections
        self.msgs = collections.deque(maxlen=100)

    def write(self, msg):
        """ Append object to the circular buffer."""
        self.msgs.append(msg)

    def flush(self):
        pass
