"""A proxy layer for the REST API.

Manipulate responses from the REST API to look like those retrieved from the
XML-RPC API.
"""

import abc
import sys

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
    def patch_set(
        self,
        patch_id,
        state=None,
        archived=None,
        commit_ref=None,
    ):
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

    def _state_id_by_name(self, name):
        """Given a partial state name, look up the state ID."""
        if len(name) == 0:
            return 0
        states = self.state_list(name, 0)
        for state in states:
            if state['name'].lower().startswith(name.lower()):
                return state['id']
        return 0

    def _patch_id_from_hash(self, project, hash):
        patch = self.patch_get_by_project_hash(project, hash)

        if patch == {}:
            sys.stderr.write("No patch has the hash provided\n")
            sys.exit(1)

        patch_id = patch['id']
        # be super paranoid
        try:
            patch_id = int(patch_id)
        except ValueError:
            sys.stderr.write("Invalid patch ID obtained from server\n")
            sys.exit(1)
        return patch_id

    def _project_id_by_name(self, linkname):
        """Given a project short name, look up the Project ID."""
        if len(linkname) == 0:
            return 0
        projects = self.project_list(linkname, 0)
        for project in projects:
            if project['linkname'] == linkname:
                return project['id']
        return 0

    def _person_ids_by_name(self, name):
        """Given a partial name or email address, return a list of the
        person IDs that match."""
        if len(name) == 0:
            return []
        people = self.person_list(name, 0)
        return [x['id'] for x in people]

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
        filters = {}

        if max_count:
            filters['max_count'] = max_count

        if archived:
            filters['archived'] = archived

        if msgid:
            filters['msgid'] = msgid

        if name:
            filters['name__icontains'] = name

        if state is not None:
            state_id = self._state_id_by_name(state)
            if state_id == 0:
                sys.stderr.write(
                    "Note: No State found matching %s*, "
                    "ignoring filter\n" % state
                )
            else:
                filters['state_id'] = state_id

        if project is not None:
            project_id = self._project_id_by_name(project)
            if project_id == 0:
                sys.stderr.write(
                    "Note: No Project found matching %s, "
                    "ignoring filter\n" % project
                )
            else:
                filters['project_id'] = project_id

        # TODO(stephenfin): This is unfortunate. We don't allow you to filter
        # by both submitter and delegate. This is due to the fact that both are
        # partial string matches and we emit a log message for each match. We
        # really need to get rid of that log and print a combined (and
        # de-duplicated) list to fix this.

        if submitter is not None:
            patches = []
            person_ids = self._person_ids_by_name(submitter)
            if len(person_ids) == 0:
                sys.stderr.write(
                    "Note: Nobody found matching *%s*\n" % submitter
                )
            else:
                for person_id in person_ids:
                    filters['submitter_id'] = person_id
                    patches += self._client.patch_list(filters)
            return patches

        if delegate is not None:
            patches = []
            delegate_ids = self._person_ids_by_name(self, delegate)
            if len(delegate_ids) == 0:
                sys.stderr.write(
                    "Note: Nobody found matching *%s*\n" % delegate
                )
            else:
                for delegate_id in delegate_ids:
                    filters['delegate_id'] = delegate_id
                    patches += self._client.patch_list(filters)
            return patches

        return self._client.patch_list(filters)

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

    def patch_set(
        self,
        patch_id,
        state=None,
        archived=None,
        commit_ref=None,
    ):
        params = {}

        if state:
            state_id = self._state_id_by_name(state)
            if state_id == 0:
                raise exceptions.APIError(
                    'No State found matching %s*' % state
                )
                sys.exit(1)

            params['state'] = state_id

        if commit_ref:
            params['commit_ref'] = commit_ref

        if archived:
            params['archived'] = archived == 'yes'

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
