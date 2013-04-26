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
#   Rob Miller (rmiller@mozilla.com)
#
# ***** END LICENSE BLOCK *****


class NoSendSender(object):
    """Non-working sender primarily used as a placeholder during
    HekaClient creation until a working sender object is provided.

    """
    def send_message(self, msg):
        """Raises NotImplementedError."""
        raise NotImplementedError


class DebugCaptureSender(object):
    def __init__(self):

        from heka.streams import DebugCaptureStream
        from heka.encoders import JSONEncoder

        self.stream = DebugCaptureStream()
        self.encoder = JSONEncoder()

    def send_message(self, msg):
        self.stream.write(self.encoder.encode(msg))

    def __getattr__(self, key):
        return getattr(self.stream, key)


def build_sender(stream, encoder):
    """
    Build a sender with a stream (string or instance)
    and an encoder by name (json|protobuf)
    """
    try:
        sender = WrappedSender(stream, encoder)
    except ValueError, ve:
        import sys
        sys.stderr.write(str(ve))
        sender = NoSendSender()
    return sender


class WrappedSender(object):
    def __init__(self, stream, encoder):
        from heka.path import resolve_name
        if isinstance(stream, basestring):
            stream = resolve_name(stream)()
        self.stream = stream

        enc_class = resolve_name(encoder)
        self.encoder = enc_class()

    def send_message(self, msg):
        data = self.encoder.encode(msg)

        self.stream.write(data)
        self.stream.flush()
