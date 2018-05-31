#!/usr/bin/env python3

"""
@author: xi
@since: 2018-04-13
"""

import collections

from . import client
from .namespace import Namespace
from .exceptions import *


class Connection(object):

    def __init__(self, on_close, zkquorum):
        """Connection.

        Args:
            on_close: Callback when connection close.
            zkquorum (str): Zookeeper quorum. Comma-separated list of hosts to connect to.
                e.g., '127.0.0.1:2181,127.0.0.1:2182,[::1]:2183'

        Raises:
            TransportError
            ZookeeperProtocolError
            NoSuchZookeeperNodeError

        """
        self._on_close = on_close
        self._zkquorum = zkquorum

        self._client = client.Client(zkquorum)
        self._namespaces = dict()

    @property
    def zkquorum(self):
        return self._zkquorum

    @property
    def client(self):
        """Client object.

        Returns:
            client.Client: Client object.

        """
        return self._client

    def close(self):
        self._on_close(self)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

    def namespaces(self):
        """List namespaces.

        Returns:
            list[str]: List of namespace names.

        """
        return self._client.namespaces()

    def namespace(self, name, create_if_not_exists=True):
        """Get a namespace object.

        Args:
            name (str): Name of the namespace.
            create_if_not_exists (bool): Create a new namespace if the required namespace does not exist.

        Returns:
            Namespace: Namespace object.

        Raises:
            NamespaceNotFoundError
            NamespaceExistError
            ServerIOError
            RequestError

            TransportError
            ZookeeperProtocolError
            ServiceProtocolError
            NoSuchZookeeperNodeError

        """
        if name in self._namespaces:
            return self._namespaces[name]

        try:
            self._client.namespace(name)
        except NamespaceNotFoundError as e:
            if create_if_not_exists:
                self._client.create_namespace(name)
            else:
                raise e

        ns = Namespace(self, name)
        self._namespaces[name] = ns
        return ns

    def __getitem__(self, name):
        """Get a namespace object.
        If the namespace does not exist, always create a new one.

        Args:
            name (str): Name of the namespace.

        Returns:
            Namespace: Namespace object.

        Raises:
            NamespaceNotFoundError
            ServerIOError
            RequestError

            TransportError
            ZookeeperProtocolError
            ServiceProtocolError
            NoSuchZookeeperNodeError

        """
        return self.namespace(name)

    def create_namespace(self, name, props=None):
        """Create a namespace.

        Args:
            name (str): Name of the namespace.
            props (dict[str, str]): Custom properties.

        Raises:
            NamespaceExistError
            ServerIOError
            RequestError

            TransportError
            ZookeeperProtocolError
            ServiceProtocolError
            NoSuchZookeeperNodeError

        """
        self._client.create_namespace(name, props)


class ConnectionPool(object):

    def __init__(self, zkquorum, max_size=10):
        """Connection pool.

        Args:
            zkquorum (str): Zookeeper quorum. Comma-separated list of hosts to connect to.
                e.g., '127.0.0.1:2181,127.0.0.1:2182,[::1]:2183'
            max_size (int): Max pool size.

        """
        self._zkquorum = zkquorum
        self._max_size = max_size
        self._conns = collections.deque()

    def connect(self):
        """Get a database connection.

        Returns:
            Connection: A connection object.

        """
        if len(self._conns) > 0:
            return self._conns.pop(0)
        else:
            return Connection(self._on_conn_close, self._zkquorum)

    def _on_conn_close(self, conn):
        """Callback when connection close.
        Not really close(delete) a connection, just put it back to the pool.

        Args:
            conn (Connection): Connection object to close.

        """
        if len(self._conns) < self._max_size:
            self._conns.append(conn)
        else:
            del conn
