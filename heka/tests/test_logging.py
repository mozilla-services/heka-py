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
from heka.client import HekaClient
from heka.logging import hook_logger
from json import loads
from mock import Mock
from nose.tools import eq_
import logging


class TestLoggingHook(object):
    logger = 'tests'

    def setUp(self):
        self.mock_stream = Mock()
        self.client = HekaClient(self.mock_stream, self.logger)

    def tearDown(self):
        del self.mock_stream

    def test_logging_handler(self):
        logger = logging.getLogger('demo')
        hook_logger('demo', self.client)
        msg = "this is an info message"
        logger.info(msg)
        # Need to decode the JSON encoded message
        jdata = loads(self.mock_stream.write.call_args[0][0][8:])
        eq_(msg, jdata['payload'])
