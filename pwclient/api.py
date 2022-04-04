"""A proxy layer for the REST API.

Manipulate responses from the REST API to look like those retrieved from the
XML-RPC API.
"""

import abc

from . import exceptions
from . import xmlrpc
from .xmlrpc import xmlrpclib


class API(metaclass=abc.ABCMeta):
    @abc.abstractmethod
    def __init__(self, server, *, username=None, password=None, token=None):
        if (username and not password) or (password and not username):
            raise exceptions.ConfigError(
                'You must provide both a username and a password or a token'
            )

        if (username and password) and token:
            raise exceptions.ConfigError(
                'You must provide either a username and password or a token, '
                'not both'
            )

    # project

    @abc.abstractmethod
    def project_list(self, search_str=None, max_count=0):
        pass

    @abc.abstractmethod
    def project_get(self, project_id):
        pass

    # person

    @abc.abstractmethod
    def person_list(self, search_str=None, max_count=0):
        pass

    @abc.abstractmethod
    def person_get(self, person_id):
        pass

    # patch

    @abc.abstractmethod
    def patch_list(
        self,
        project,
        submitter,
        delegate,
        state,
        archived,
        msgid,
        name,
        max_count=None,
    ):
        pass

    @abc.abstractmethod
    def patch_get(self, patch_id):
        pass

    @abc.abstractmethod
    def patch_get_by_hash(self, hash):
        pass

    @abc.abstractmethod
    def patch_get_by_project_hash(self, project, hash):
        pass

    @abc.abstractmethod
    def patch_get_mbox(self, patch_id):
        pass

    @abc.abstractmethod
    def patch_get_diff(self, patch_id):
        pass

    @abc.abstractmethod
    def patch_set(self, patch_id, params):
        pass

    # states

    @abc.abstractmethod
    def state_list(self, search_str=None, max_count=0):
        pass

    @abc.abstractmethod
    def state_get(self, state_id):
        pass

    # checks

    @abc.abstractmethod
    def check_list(self):
        pass

    @abc.abstractmethod
    def check_get(self, check_id):
        pass

    @abc.abstractmethod
    def check_create(
        self,
        patch_id,
        context,
        state,
        target_url="",
        description="",
    ):
        pass


class XMLRPC(API):
    def __init__(self, server, *, username=None, password=None, token=None):
        super().__init__(
            server,
            username=username,
            password=password,
            token=token,
        )

        if token:
            raise exceptions.ConfigError(
                'The XML-RPC API does not support API tokens'
            )

        self._server = server

        transport = xmlrpc.Transport(self._server)
        if username and password:
            transport.set_credentials(username, password)

        try:
            rpc = xmlrpc.xmlrpclib.Server(self._server, transport=transport)
        except (IOError, OSError):
            raise exceptions.APIError(f'Unable to connect to {self._server}')

        self._client = rpc

    # project

    def project_list(self, search_str=None, max_count=0):
        return self._client.project_list(search_str, max_count)

    def project_get(self, project_id):
        return self._client.project_get(project_id)

    # person

    def person_list(self, search_str=None, max_count=0):
        return self._client.person_list(search_str, max_count)

    def person_get(self, person_id):
        return self._client.person_get(person_id)

    # patch

    def patch_list(self, filt=None):
        return self._client.patch_list(filt)

    def patch_get(self, patch_id):
        return self._client.patch_get(patch_id)

    def patch_get_by_hash(self, hash):
        return self._client.patch_get_by_hash(hash)

    def patch_get_by_project_hash(self, project, hash):
        return self._client.patch_get_by_project_hash(project, hash)

    def patch_get_mbox(self, patch_id):
        return self._client.patch_get_mbox(patch_id)

    def patch_get_diff(self, patch_id):
        return self._client.patch_get_diff(patch_id)

    def patch_set(self, patch_id, params):
        return self._client.patch_set(patch_id, params)

    # states

    def state_list(self, search_str=None, max_count=0):
        return self._client.state_list(search_str, max_count)

    def state_get(self, state_id):
        return self._client.state_get(state_id)

    # checks

    # TODO(stephenfin): Add support for filters
    def check_list(self):
        return self._client.check_list()

    def check_get(self, check_id):
        return self._client.check_get(check_id)

    def check_create(
        self,
        patch_id,
        context,
        state,
        target_url="",
        description="",
    ):
        try:
            return self._client.check_create(
                patch_id,
                context,
                state,
                target_url,
                description,
            )
        except xmlrpclib.Fault as f:
            raise exceptions.APIError(
                'Error creating check: %s' % f.faultString
            )
