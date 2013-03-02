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
#   Rob Miller (rmiller@mozilla.com)
#
# ***** END LICENSE BLOCK *****
from heka.decorators.base import HekaDecorator


class timeit(HekaDecorator):
    """Lazily decorate any callable with a heka timer."""
    def predicate(self):
        client = self.client
        timer_name = self.args[0] if self.args else self._fn.__name__
        if (timer_name in client._disabled_timers or
            '*' in client._disabled_timers):
            return False
        return super(timeit, self).predicate()

    def heka_call(self, *args, **kwargs):
        if self.args and 'name' in self.kwargs:
            # Don't pass name in twice if it was set as an arg
            self.kwargs.pop('name')
        with self.client.timer(*self.args, **self.kwargs):
            return self._fn(*args, **kwargs)


class incr_count(HekaDecorator):
    """Lazily decorate any callable w/ a wrapper that will increment a
    heka counter whenever the callable is invoked.

    """
    def heka_call(self, *args, **kwargs):
        if 'count' not in self.kwargs:
            self.kwargs['count'] = 1
        try:
            result = self._fn(*args, **kwargs)
        finally:
            self.client.incr(*self.args, **self.kwargs)
        return result
