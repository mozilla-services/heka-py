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
"""
This module contains a Heka decorator base class and some additional helper
code. The primary reason for these abstractions is 'deferred configuration'.
Decorators are evaluated by Python at import time, but often the configuration
needed for a Heka client, which might negate (or change) the behavior of a
Heka decorator, isn't available until later, after some config parsing code
has executed. This code provides a mechanism to have a function get wrapped in
one way (or not at all) when the decorator is originally evaluated, but then to
be wrapped differently once the config has loaded and the desired final
behavior has been established.
"""
import functools

from heka.decorators.util import return_fq_name
from heka.holder import CLIENT_HOLDER
from heka.util import json


class HekaDecorator(object):
    """Base class for Heka decorators

    Designed to support 'rebinding' of the actual decorator method once
    Heka configuration has actually been loaded. The first time the
    decorated function is invoked, the `predicate` method will be
    called. If the result is True, then `heka_call` (intended to be
    implemented by subclasses) will be used as the decorator. If the
    `predicate` returns False, then `_invoke` (which by default does
    nothing but call the wrapped function) will be used as the
    decorator.

    """
    def __init__(self, *args, **kwargs):
        """Create the decorator

        :param client: Optional HekaClient instance. Will override any
                       `client_name` value that may be specified, if
                       provided.
        :param client_name: Optional `logger` name of a HekaClient
                            instance that is stored in the
                            CLIENT_HOLDER

        If neither the `client` nor `client_name` parameters are
        specified, then CLIENT_HOLDER.default_client will be used.

        """
        self._client = kwargs.pop('client', None)
        self.client_name = kwargs.pop('client_name', '')
        self.args = args
        self.kwargs = kwargs
        if len(args) == 1 and len(kwargs) == 0 and callable(args[0]):
            # bare decorator, i.e. no arguments
            self.args = tuple()
            self.set_fn(args[0])
        else:
            self._fn = None

    @property
    def decorator_name(self):
        return self.__class__.__name__

    @property
    def client(self):
        if self._client is None:
            if self.client_name:
                self._client = CLIENT_HOLDER.get_client(self.client_name)
            else:
                self._client = CLIENT_HOLDER.default_client
        return self._client

    def predicate(self):
        """Predicate used to determine if function is rebound during
        the rebind process

        True return value will rebind such that `self.heka_call`
        becomes the decorator function, False will rebind such that
        `self._invoke` becomes the decorator function.

        """
        disabled = []
        if self.decorator_name in disabled:
            return False
        return True

    def set_fn(self, fn):
        """Sets the function and stores the full dotted notation fn
        name for later use.#

        :param fn: Actual function that we are decorating.

        """
        self._fn = fn
        if fn is None:
            self._fn_fq_name = None
        elif isinstance(fn, HekaDecorator):
            self._fn_fq_name = fn._fn_fq_name
        else:
            self._fn_fq_name = return_fq_name(fn)

        if self._fn != None:
            self._update_decoratorchain()

        if self._fn_fq_name and 'name' not in self.kwargs:
            self.kwargs['name'] = self._fn_fq_name

    def _update_decoratorchain(self):
        if not hasattr(self, '_heka_decorators'):
            self._heka_decorators = set()

        if self.kwargs is None:
            sorted_kw = None
        else:
            sorted_kw = json.dumps(self.kwargs)

        if self.args is None:
            sorted_args = None
        else:
            sorted_args = tuple(self.args)

        key = (self.__class__, sorted_args, sorted_kw)

        self._heka_decorators.add(key)

        # Add any decorators from the wrapped callable
        if hasattr(self._fn, '_heka_decorators'):
            self._heka_decorators.update(self._fn._heka_decorators)

    def __call__(self, *args, **kwargs):
        if self._fn is None:
            # We finally got passed the function, set it and return ourself
            self.set_fn(args[0])
            return self

        if self.predicate():
            replacement = self.heka_call
        else:
            replacement = self._invoke
        self.__call__ = replacement
        return replacement(*args, **kwargs)

    def __get__(self, instance, owner):
        """Descriptor lookup logic to implement bound methods."""
        # If accessed directly from the class, return the decorator itself.
        if instance is None:
            return self
        # If accessed via an instance, bind it as the first argument.
        return functools.partial(self, instance)

    @property
    def __name__(self):
        """Support the use of functools.wraps."""
        return self._fn.__name__

    def _invoke(self, *args, **kwargs):
        """Call the wrapped function."""
        return self._fn(*args, **kwargs)

    def heka_call(self, *args, **kwargs):
        """Actual heka activity happens here. Implemented by subclasses."""
        raise NotImplementedError
