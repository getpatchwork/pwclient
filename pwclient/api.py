"""A proxy layer for the REST API.

Manipulate responses from the REST API to look like those retrieved from the
XML-RPC API.
"""

import abc
import base64
import json
import http
import re
import sys
import urllib.error
import urllib.parse
import urllib.request

from . import exceptions
from . import xmlrpc
from . import __version__
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
        hash,
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
    def check_list(self, patch_id, user):
        pass

    @abc.abstractmethod
    def check_get(self, patch_id, check_id):
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

    @staticmethod
    def _decode_patch(patch):
        # Some values are transferred as Binary data, these are encoded in
        # utf-8. As of Python 3.9 xmlrpclib.Binary.__str__ however assumes
        # latin1, so decode explicitly
        return {
            k: v.data.decode('utf-8') if isinstance(v, xmlrpclib.Binary) else v
            for k, v in patch.items()
        }

    def patch_list(
        self,
        project,
        submitter,
        delegate,
        state,
        archived,
        msgid,
        name,
        hash,
        max_count=None,
    ):
        filters = {}

        if max_count:
            filters['max_count'] = max_count

        if archived is not None:
            filters['archived'] = archived

        if msgid:
            filters['msgid'] = msgid

        if name:
            filters['name__icontains'] = name

        if hash:
            filters['hash'] = hash

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
            return [self._decode_patch(patch) for patch in patches]

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
            return [self._decode_patch(patch) for patch in patches]

        patches = self._client.patch_list(filters)
        return [self._decode_patch(patch) for patch in patches]

    def patch_get(self, patch_id):
        patch = self._client.patch_get(patch_id)
        if patch == {}:
            raise exceptions.APIError(
                'Unable to fetch patch %d; does it exist?' % patch_id
            )

        return self._decode_patch(patch)

    def patch_get_by_hash(self, hash):
        return self._client.patch_get_by_hash(hash)

    def patch_get_by_project_hash(self, project, hash):
        return self._client.patch_get_by_project_hash(project, hash)

    def patch_get_mbox(self, patch_id):
        patch = self.patch_get(patch_id)

        mbox = self._client.patch_get_mbox(patch_id)
        if len(mbox) == 0:
            raise exceptions.APIError(
                'Unable to fetch mbox for patch %d; does it exist?' % patch_id
            )

        return mbox, patch['filename']

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

        try:
            return self._client.patch_set(patch_id, params)
        except xmlrpclib.Fault as f:
            raise exceptions.APIError(
                'Error updating patch: %s' % f.faultString
            )

    # states

    def state_list(self, search_str=None, max_count=0):
        return self._client.state_list(search_str, max_count)

    def state_get(self, state_id):
        return self._client.state_get(state_id)

    # checks

    def check_list(self, patch_id, user):
        filters = {}

        if patch_id is not None:
            filters['patch_id'] = patch_id

        if user is not None:
            filters['user'] = user

        return self._client.check_list(filters)

    def check_get(self, patch_id, check_id):
        # patch_id is not necessary for the XML-RPC API
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


class REST(API):
    def __init__(self, server, *, username=None, password=None, token=None):

        # TODO(stephenfin): We want to deprecate this behavior at some point
        parsed_server = urllib.parse.urlparse(server)
        scheme = parsed_server.scheme or 'http'
        hostname = parsed_server.netloc
        path = parsed_server.path
        if path.rstrip('/') == '/xmlrpc':
            path = '/api'

        self._server = f'{scheme}://{hostname}{path}'

        self._username = username
        self._password = password
        self._token = token

    def _generate_headers(self, additional_headers=None):
        headers = {
            'User-Agent': f'pwclient ({__version__})',
        }

        if self._token:
            pass

        if self._username:
            credentials = base64.b64encode(
                f'{self._username}:{self._password}'.encode('ascii')
            ).decode('ascii')
            headers['Authorization'] = f'Basic {credentials}'

        if additional_headers:
            headers = dict(headers, **additional_headers)

        return headers

    def _get(self, url):
        request = urllib.request.Request(
            url=url, method='GET', headers=self._generate_headers()
        )
        try:
            with urllib.request.urlopen(request) as resp:
                data = resp.read()
                headers = resp.getheaders()
        except urllib.error.HTTPError as exc:
            # the XML-RPC API returns an empty body, annoyingly, so we must
            # emulate this
            if exc.status == http.HTTPStatus.NOT_FOUND:
                return {}, {}

            sys.stderr.write('Request failed\n\n')
            sys.stderr.write('Response:\n')
            sys.stderr.write(exc.read().decode('utf-8'))
            sys.exit(1)

        return data, headers

    def _post(self, url, data):
        request = urllib.request.Request(
            url=url,
            data=json.dumps(data).encode('utf-8'),
            method='POST',
            headers=self._generate_headers(
                {
                    'Content-Type': 'application/json',
                },
            ),
        )
        try:
            with urllib.request.urlopen(request) as resp:
                data = resp.read()
                headers = resp.getheaders()
        except urllib.error.HTTPError as exc:
            sys.stderr.write('Request failed\n\n')
            sys.stderr.write('Response:\n')
            sys.stderr.write(exc.read().decode('utf-8'))
            sys.exit(1)

        return data, headers

    def _put(self, url, data):
        request = urllib.request.Request(
            url=url,
            data=json.dumps(data).encode('utf-8'),
            method='PATCH',
            headers=self._generate_headers(
                {
                    'Content-Type': 'application/json',
                },
            ),
        )
        try:
            with urllib.request.urlopen(request) as resp:
                data = resp.read()
                headers = resp.getheaders()
        except urllib.error.HTTPError as exc:
            sys.stderr.write('Request failed\n\n')
            sys.stderr.write('Response:\n')
            sys.stderr.write(exc.read().decode('utf-8'))
            sys.exit(1)

        return data, headers

    def _create(
        self,
        resource_type,
        data,
        *,
        resource_id=None,
        subresource_type=None,
    ):
        url = f'{self._server}/{resource_type}/'
        if resource_id:
            url = f'{url}{resource_id}/{subresource_type}/'
        data, _ = self._post(url, data)
        return json.loads(data)

    def _update(
        self,
        resource_type,
        resource_id,
        data,
        *,
        subresource_type=None,
        subresource_id=None,
    ):
        url = f'{self._server}/{resource_type}/{resource_id}/'
        if subresource_id:
            url = f'{url}{subresource_type}/{subresource_id}/'
        data, _ = self._put(url, data)
        return json.loads(data)

    def _detail(
        self,
        resource_type,
        resource_id,
        params=None,
        *,
        subresource_type=None,
        subresource_id=None,
    ):
        url = f'{self._server}/{resource_type}/{resource_id}/'
        if subresource_type:
            url = f'{url}{subresource_type}/{subresource_id}/'
        if params:
            url = f'{url}?{urllib.parse.urlencode(params)}'
        data, _ = self._get(url)
        return json.loads(data)

    def _list(
        self,
        resource_type,
        params=None,
        *,
        resource_id=None,
        subresource_type=None,
    ):
        url = f'{self._server}/{resource_type}/'
        if resource_id:
            url = f'{url}{resource_id}/{subresource_type}/'
        if params:
            url = f'{url}?{urllib.parse.urlencode(params)}'
        data, _ = self._get(url)
        return json.loads(data)

    # project

    @staticmethod
    def _project_to_dict(obj):
        """Serialize a project response.

        Return a trimmed down dictionary representation of the API response
        that matches what we got from the XML-RPC API.
        """
        return {
            'id': obj['id'],
            'linkname': obj['linkname']
            if 'linkname' in obj
            else obj['link_name'],
            'name': obj['name'],
        }

    def project_list(self, search_str=None, max_count=0):
        # we could implement these but we don't need them
        if search_str:
            raise NotImplementedError(
                'The search_str parameter is not supported',
            )

        if max_count:
            raise NotImplementedError(
                'The max_count parameter is not supported',
            )

        projects = self._list('projects')
        return [self._project_to_dict(project) for project in projects]

    def project_get(self, project_id):
        project = self._detail('projects', project_id)
        return self._project_to_dict(project)

    # person

    @staticmethod
    def _person_to_dict(obj):
        """Serialize a person response.

        Return a trimmed down dictionary representation of the API response
        that matches what we got from the XML-RPC API.
        """
        return {
            'id': obj['id'],
            'email': obj['email'],
            'name': obj['name'] if obj['name'] else obj['email'],
            'user': obj['user']['username'] if obj['username'] else '',
        }

    def person_list(self, search_str=None, max_count=0):
        # we could implement these but we don't need them
        if search_str:
            raise NotImplementedError(
                'The search_str parameter is not supported',
            )

        if max_count:
            raise NotImplementedError(
                'The max_count parameter is not supported',
            )

        people = self._list('people')
        return [self._person_to_dict(person) for person in people]

    def person_get(self, person_id):
        person = self._detail('people', person_id)
        return self._person_to_dict(person)

    # patch

    @staticmethod
    def _patch_to_dict(obj):
        """Serialize a patch response.

        Return a trimmed down dictionary representation of the API response
        that matches what we got from the XML-RPC API.
        """

        def _format_person(person):
            if not person:
                return ''

            if person['name']:
                return f"{person['name']} <{person['email']}>"
            return person['email']

        def _format_user(user):
            if not user:
                return ''

            return user['username']

        return {
            'id': obj['id'],
            'date': obj['date'],
            'filename': obj.get('filename') or '',
            'msgid': obj['msgid'],
            'name': obj['name'],
            'project': obj['project']['name'],
            'project_id': obj['project']['id'],
            'state': obj['state'],
            'state_id': '',  # NOTE: this isn't exposed
            'archived': obj['archived'],
            'submitter': _format_person(obj['submitter']),
            'submitter_id': obj['submitter']['id'],
            'delegate': _format_user(obj['delegate']),
            'delegate_id': obj['delegate']['id'] if obj['delegate'] else '',
            'commit_ref': obj['commit_ref'] or '',
            'hash': obj['hash'] or '',
        }

    def patch_list(
        self,
        project,
        submitter,
        delegate,
        state,
        archived,
        msgid,
        name,
        hash,
        max_count=None,
    ):
        # we could implement these but we don't need them
        if max_count:
            raise NotImplementedError(
                'The max_count parameter is not supported',
            )

        filters = {}

        if state is not None:
            # we slugify this since that's what the API expects
            filters['state'] = state.lower().replace(' ', '-')

        if project is not None:
            filters['project'] = project

        if hash is not None:
            filters['hash'] = hash

        patches = self._list('patches', params=filters)
        return [self._patch_to_dict(patch) for patch in patches]

    def patch_get(self, patch_id):
        patch = self._detail('patches', patch_id)
        return self._patch_to_dict(patch)

    def patch_get_by_hash(self, hash):
        patches = self._list('patches', {'hash': hash})
        if len(patches) != 1:
            return {}  # emulate xmlrpc behavior
        return self._patch_to_dict(patches[0])

    def patch_get_by_project_hash(self, project, hash):
        patches = self._list('patches', {'project': project, 'hash': hash})
        if len(patches) != 1:
            return {}  # emulate xmlrpc behavior
        return self._patch_to_dict(patches[0])

    def patch_get_mbox(self, patch_id):
        patch = self._detail('patches', patch_id)
        data, headers = self._get(patch['mbox'])
        header = ''
        for name, value in headers:
            if name.lower() == 'content-disposition':
                header = value
                break
        header_re = re.search('filename=(.+)', header)
        if not header_re:
            raise Exception('filename header was missing from the response')

        filename = header_re.group(1)[:-6]  # remove the extension

        return data.decode('utf-8'), filename

    def patch_get_diff(self, patch_id):
        patch = self._detail('patches', patch_id)
        return patch['diff']

    def patch_set(
        self,
        patch_id,
        state=None,
        archived=None,
        commit_ref=None,
    ):
        params = {}

        if state is not None:
            # we slugify this since that's what the API expects
            params['state'] = state.lower().replace(' ', '-')

        if commit_ref is not None:
            params['commit_ref'] = commit_ref

        if archived is not None:
            params['archived'] = archived

        patch = self._update('patches', patch_id, params)
        return self._patch_to_dict(patch)

    # states

    # Patch states are not exposed via the REST API, on the basis that they
    # will eventually be a static list as opposed to something configurable. As
    # such, we simply emulate the behavior here.

    def state_list(self, search_str=None, max_count=0):
        raise NotImplementedError('The REST API does not expose state objects')

    def state_get(self, state_id):
        raise NotImplementedError('The REST API does not expose state objects')

    # checks

    @staticmethod
    def _check_to_dict(obj, patch):
        """Serialize a check response.

        Return a trimmed down dictionary representation of the API response
        that matches what we got from the XML-RPC API.
        """
        return {
            'id': obj['id'],
            'date': obj['date'],
            'patch': patch['name'],
            'patch_id': patch['id'],
            'user': obj['user']['username'] if obj['user'] else '',
            'user_id': obj['user']['id'],
            'state': obj['state'],
            'target_url': obj['target_url'],
            'description': obj['description'],
            'context': obj['context'],
        }

    def check_list(self, patch_id, user):
        if not patch_id:
            raise NotImplementedError(
                'The REST API does not allow listing of all checks by '
                'project; listing of checks requires a target patch'
            )

        filters = {}

        if user is not None:
            filters['user'] = user

        # this is icky, but alas we don't provide this information in the
        # response
        patch = self._detail(
            'patches',
            patch_id,
        )
        checks = self._list(
            'patches',
            filters,
            resource_id=patch_id,
            subresource_type='checks',
        )
        return [self._check_to_dict(check, patch) for check in checks]

    def check_get(self, patch_id, check_id):
        if not patch_id:
            raise NotImplementedError(
                'The REST API does not allow listing of all checks by '
                'project; listing of checks requires a target patch'
            )

        # this is icky, but alas we don't provide this information in the
        # response
        patch = self._detail(
            'patches',
            patch_id,
        )
        check = self._detail(
            'patches',
            resource_id=patch_id,
            subresource_type='checks',
            subresource_id=check_id,
        )
        return self._check_to_dict(check, patch)

    def check_create(
        self,
        patch_id,
        context,
        state,
        target_url="",
        description="",
    ):
        check = self._create(
            'patches',
            resource_id=patch_id,
            subresource_type='checks',
            data={
                'context': context,
                'state': state,
                'target_url': target_url,
                'description': description,
            },
        )
        patch = self._detail(
            'patches',
            patch_id,
        )
        return self._check_to_dict(check, patch)
