# ***** BEGIN LICENSE BLOCK *****
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this file,
# You can obtain one at http://mozilla.org/MPL/2.0/.
#
# Contributor(s):
#   Rob Miller (rmiller@mozilla.com)
#   Victor Ng (vng@mozilla.com)
#
# ***** END LICENSE BLOCK *****
import threading

from heka.client import HekaClient
from heka.config import client_from_dict_config


class HekaClientHolder(object):
    """Used as a singleton class to hold references to HekaClient
    instances

    Also holds any required process-wide config data.

    """
    def __init__(self):
        self._clients = dict()
        self._default_clientname = None
        self.lock = threading.Lock()  # write lock for adding clients

    def get_client(self, name):
        """Return the specified HekaClient, creating it if it doesn't
        exist.

        .. note::

            Auto-created HekaClient instances will *not* yet be usable,
            it is the downstream developer's responsibility to provide
            them with a working stream.

        :param name: String token identifying the client, also used as the
                     client's `logger` value.

        """
        if name is None:
            return None

        client = self._clients.get(name)
        if client is None:
            with self.lock:
                # check again to make sure nobody else got the lock first
                client = self._clients.get(name)
                if client is None:
                    client = HekaClient(stream=None, logger=name)
                    if (not self._clients
                        and not self._default_clientname):
                        # first one, set as default
                        self._default_clientname = name
                    self._clients[name] = client


        return client

    def set_client(self, name, client):
        """Provides a way to add a pre-existing HekaClient to the ones
        stored in the holder.

        """
        with self.lock:
            self._clients[name] = client
            if len(self._clients) == 1:
                # first one, set as default
                self._default_clientname = name

    def set_default_client_name(self, name):
        """Convenience method for specifying what should be the default
        client.

        """
        self._default_clientname = name

    @property
    def default_client(self):
        """
        Return the default HekaClient (as specified by the
        `self._default_clientname`).
        """
        return self._clients.get(self._default_clientname, None)

    def delete_client(self, name):
        """Deletes the specified client from the set of stored clients.

        :param name: Name of the client object to delete.

        """
        if name in self._clients:
            del self._clients[name]
        if self._default_clientname == name:
            self._default_clientname = None


CLIENT_HOLDER = HekaClientHolder()


def get_client(name, config_dict=None):
    """Return client of the specified name from the CLIENT_HOLDER.

    :param name: String token to identify the HekaClient, also used for
                 the default `logger` value of that client.
                 `ValueError` will be raised if a config is provided
                 w/ a different `logger` value.

                 If name isn't specified, the default client will be
                 returned if one exists
    :param config_dict: Configuration dictionary to be applied to the
                        fetched client.

    """
    client = CLIENT_HOLDER.get_client(name)

    if config_dict:
        logger = config_dict.get('logger')
        if logger and logger != name:
            raise ValueError('Config `logger` value must either match `name` '
                             'argument or be left blank.')
        if not logger:
            config_dict['logger'] = name
        client = client_from_dict_config(config_dict, client=client)
    return client
