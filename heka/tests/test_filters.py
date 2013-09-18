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
from heka.client import HekaClient
from heka.client import SEVERITY
from heka.streams import DebugCaptureStream
from heka.tests.helpers import decode_message
from nose.tools import eq_, ok_
import random


class TestHekaClientFilters(object):
    logger = 'tests'
    timer_name = 'test'

    def setUp(self):
        self.stream = DebugCaptureStream()
        self.client = HekaClient(self.stream, self.logger)

    def tearDown(self):
        del self.stream
        del self.client

    def test_severity_max(self):
        from heka.filters import severity_max_provider
        self.client.filters = [severity_max_provider(severity=SEVERITY.ERROR)]
        payload = 'foo'
        self.client.debug(payload)
        self.client.info(payload)
        self.client.warn(payload)
        self.client.error(payload)
        self.client.exception(payload)
        self.client.critical(payload)
        # only half of the messages should have gone out
        eq_(len(self.stream.msgs), 3)
        # make sure it's the right half
        for json_msg in self.stream.msgs:
            msg = self._extract_msg(json_msg)
            ok_(msg.severity <= SEVERITY.ERROR)

    def test_type_blacklist(self):
        from heka.filters import type_blacklist_provider
        type_blacklist = type_blacklist_provider(types=set(['foo']))
        self.client.filters = [type_blacklist]
        choices = ['foo', 'bar']
        notfoos = 0
        for i in range(10):
            choice = random.choice(choices)
            if choice != 'foo':
                notfoos += 1
            self.client.heka(choice, payload='msg')
        eq_(len(self.stream.msgs), notfoos)

    def test_type_whitelist(self):
        from heka.filters import type_whitelist_provider
        type_whitelist = type_whitelist_provider(types=set(['foo']))
        self.client.filters = [type_whitelist]
        choices = ['foo', 'bar']
        foos = 0
        for i in range(10):
            choice = random.choice(choices)
            if choice == 'foo':
                foos += 1
            self.client.heka(choice, payload='msg')
        eq_(len(self.stream.msgs), foos)

    def test_type_severity_max(self):
        from heka.filters import type_severity_max_provider
        config = {'types': {'foo': {'severity': 3},
                            'bar': {'severity': 5},
                            },
                  }
        type_severity_max = type_severity_max_provider(**config)
        self.client.filters = [type_severity_max]
        for msgtype in ['foo', 'bar']:
            for sev in range(8):
                self.client.heka(msgtype, severity=sev, payload='msg')
        eq_(len(self.stream.msgs), 10)
        msgs = [self._extract_msg(msg) for msg in self.stream.msgs]
        foos = [msg for msg in msgs if msg.type == 'foo']
        eq_(len(foos), 4)
        bars = [msg for msg in msgs if msg.type == 'bar']
        eq_(len(bars), 6)

    def _extract_msg(self, bytes):
        h, m = decode_message(bytes)
        return m
