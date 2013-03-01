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
#   Rob Miller (rmiller@mozilla.com)
#
# ***** END LICENSE BLOCK *****
from heka.exceptions import EnvironmentNotFoundError
from heka.client import HekaClient
from heka.config import client_from_text_config
from heka.config import client_from_dict_config
from heka.senders import DebugCaptureSender
from mock import Mock
from nose.tools import assert_raises, eq_, ok_

import json
import os

# sys is used in a mock patch, so flake8 may yell at you
import sys  # NOQA


MockSender = Mock()


def test_simple_config():
    cfg_txt = """
    [heka_config]
    sender_class = heka.senders.DebugCaptureSender
    """
    client = client_from_text_config(cfg_txt, 'heka_config')
    eq_(client.__class__, HekaClient)
    eq_(client.sender.__class__, DebugCaptureSender)


def test_multiline_config():
    cfg_txt = """
    [heka_config]
    sender_class = heka.tests.test_config.MockSender
    sender_multi = foo
                   bar
    """
    client = client_from_text_config(cfg_txt, 'heka_config')
    ok_(isinstance(client.sender, Mock))
    MockSender.assert_called_with(multi=['foo', 'bar'])


def test_environ_vars():
    env_var = 'SENDER_TEST'
    marker = object()
    orig_value = marker
    if env_var in os.environ:
        orig_value = os.environ[env_var]
    os.environ[env_var] = 'heka.senders.DebugCaptureSender'
    cfg_txt = """
    [test1]
    sender_class = ${SENDER_TEST}
    """
    client = client_from_text_config(cfg_txt, 'test1')
    eq_(client.sender.__class__, DebugCaptureSender)

    cfg_txt = """
    [test1]
    sender_class = ${NO_SUCH_VAR}
    """
    assert_raises(EnvironmentNotFoundError, client_from_text_config,
                  cfg_txt, 'test1')
    if orig_value is not marker:
        os.environ[env_var] = orig_value
    else:
        del os.environ[env_var]


def test_int_bool_conversions():
    cfg_txt = """
    [heka_config]
    sender_class = heka.tests.test_config.MockSender
    sender_integer = 123
    sender_true1 = True
    sender_true2 = t
    sender_true3 = Yes
    sender_true4 = on
    sender_false1 = false
    sender_false2 = F
    sender_false3 = no
    sender_false4 = OFF
    """
    client = client_from_text_config(cfg_txt, 'heka_config')
    ok_(isinstance(client.sender, Mock))
    MockSender.assert_called_with(integer=123, true1=True, true2=True,
                                  true3=True, true4=True, false1=False,
                                  false2=False, false3=False, false4=False)


def test_global_config():
    cfg_txt = """
    [heka]
    sender_class = heka.senders.DebugCaptureSender
    global_foo = bar
    global_multi = one
                   two
    """
    client_from_text_config(cfg_txt, 'heka')
    from heka.holder import CLIENT_HOLDER
    expected = {'foo': 'bar', 'multi': ['one', 'two']}
    eq_(expected, CLIENT_HOLDER.global_config)


def test_filters_config():
    cfg_txt = """
    [heka]
    sender_class = heka.senders.DebugCaptureSender
    [heka_filter_sev_max]
    provider = heka.filters.severity_max_provider
    severity = 6
    [heka_filter_type_whitelist]
    provider = heka.filters.type_whitelist_provider
    types = foo
            bar
            baz
    """
    client = client_from_text_config(cfg_txt, 'heka')
    eq_(len(client.filters), 2)

    severity_max = [x for x in client.filters if x.func_name == 'severity_max']
    eq_(len(severity_max), 1)
    severity_max = severity_max[0]
    eq_(severity_max.func_name, 'severity_max')
    msg = {'severity': 6}
    ok_(severity_max(msg))
    msg = {'severity': 7}
    ok_(not severity_max(msg))

    type_whitelist = [x for x in client.filters if x.func_name == 'type_whitelist']
    eq_(len(type_whitelist), 1)
    type_whitelist = type_whitelist[0]
    eq_(type_whitelist.func_name, 'type_whitelist')
    msg = {'type': 'bar'}
    ok_(type_whitelist(msg))
    msg = {'type': 'bawlp'}
    ok_(not type_whitelist(msg))


def test_plugins_config():
    cfg_txt = """
    [heka]
    sender_class = heka.senders.DebugCaptureSender
    [heka_plugin_dummy]
    provider=heka.tests.plugin:config_plugin
    verbose=True
    foo=bar
    some_list = dog
                cat
                bus
    port=8080
    host=lolcathost
    """
    client = client_from_text_config(cfg_txt, 'heka')
    actual = client.dummy(verbose=True)
    expected = {'host': 'lolcathost',
                'foo': 'bar',
                'some_list': ['dog', 'cat', 'bus'],
                'port': 8080}
    eq_(actual, expected)


def test_plugin_override():
    cfg_txt = """
    [heka]
    sender_class = heka.senders.DebugCaptureSender

    [heka_plugin_exception]
    override=True
    provider=heka.tests.plugin:config_plugin
    """
    client = client_from_text_config(cfg_txt, 'heka')
    eq_('dummy', client.dummy.heka_name)

    cfg_txt = """
    [heka]
    sender_class = heka.senders.DebugCaptureSender
    [heka_plugin_exception]
    provider=heka.tests.plugin_exception:config_plugin
    """
    # Failure to set an override argument will throw an exception
    assert_raises(SyntaxError, client_from_text_config, cfg_txt, 'heka')


def test_load_config_multiple_times():
    cfg = {'logger': 'addons-marketplace-dev',
           'sender': {'class': 'heka.senders.UdpSender',
           'host': ['logstash1', 'logstash2'],
           'port': '5566'}}

    client_from_dict_config(cfg)
    client_from_dict_config(cfg)


def test_clients_expose_configuration():
    cfg = {'logger': 'addons-marketplace-dev',
           'sender': {'class': 'heka.senders.UdpSender',
           'host': ['logstash1', 'logstash2'],
           'port': '5566'}}

    client = client_from_dict_config(cfg)
    eq_(client._config, json.dumps(cfg))
