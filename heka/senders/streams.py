# ***** BEGIN LICENSE BLOCK *****
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this file,
# You can obtain one at http://mozilla.org/MPL/2.0/.
#
# The Initial Developer of the Original Code is the Mozilla Foundation.
# Portions created by the Initial Developer are Copyright (C) 2012
# the Initial Developer. All Rights Reserved.
#
# Contributor(s):
#   Victor Ng (vng@mozilla.com)
#
# ***** END LICENSE BLOCK *****



# All streams must implement 2 methods :
# 
#     def write(byte_data):
#         # byte_data is a set of bytes which are written directly to
#         # the stream
#     
#     def flush():
#         # force any buffered data to be flushed down.  May be
#         # implemented as a no-op.

