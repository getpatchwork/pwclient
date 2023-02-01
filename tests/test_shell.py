from unittest import mock

import pytest

from pwclient import api
from pwclient import checks
from pwclient import exceptions
from pwclient import patches
from pwclient import projects
from pwclient import shell
from pwclient import states
from pwclient import utils

DEFAULT_PROJECT = 'defaultproject'
_UNSET = object()


class FakeConfig(object):
    def __init__(self, updates=None):
        self._data = {
            'options': {
                'default': DEFAULT_PROJECT,
            },
            DEFAULT_PROJECT: {
                'url': 'https://example.com/',
            },
        }

        # merge updates into defaults
        for section in updates or {}:
            if section not in self._data:
                self._data[section] = {}

            for option in updates[section]:
                self._data[section][option] = updates[section][option]

    def write(self, fd):
        pass

    def read(self, files):
        pass

    def add_section(self, section):
        self._data[section] = {}

    def has_section(self, section):
        return section in self._data

    def has_option(self, section, option):
        return self.has_section(section) and option in self._data[section]

    def set(self, section, option, value):
        if section not in self._data:
            raise utils.configparser.NoSectionError(section)

        self._data[section][option] = value

    def get(self, section, option, *, fallback=_UNSET):
        if section not in self._data:
            raise utils.configparser.NoSectionError(section)

        if option not in self._data[section] and fallback is _UNSET:
            raise utils.configparser.NoOptionError(option, section)

        return self._data[section].get(option) or fallback

    def getboolean(self, section, option):
        return self.get(section, option)


def test_no_args(capsys):
    with pytest.raises(SystemExit):
        shell.main([])

    captured = capsys.readouterr()

    assert 'usage: pwclient [-h]' in captured.out
    assert captured.err == ''


def test_help(capsys):
    with pytest.raises(SystemExit):
        shell.main(['-h'])

    captured = capsys.readouterr()

    assert 'usage: pwclient [-h]' in captured.out
    assert captured.err == ''


@mock.patch.object(utils.configparser, 'ConfigParser')
def test_no_project(mock_config, capsys):
    fake_config = FakeConfig()
    del fake_config._data['options']['default']

    mock_config.return_value = fake_config

    with pytest.raises(SystemExit):
        shell.main(['get', '1'])

    captured = capsys.readouterr()

    assert 'No default project configured' in captured.err
    assert captured.out == ''


@mock.patch.object(utils.configparser, 'ConfigParser')
def test_no_project_url(mock_config, capsys):
    fake_config = FakeConfig()
    del fake_config._data[DEFAULT_PROJECT]['url']

    mock_config.return_value = fake_config

    with pytest.raises(SystemExit):
        shell.main(['get', '1'])

    captured = capsys.readouterr()

    assert 'No URL for project %s' % DEFAULT_PROJECT in captured.err
    assert captured.out == ''


@mock.patch.object(utils.configparser, 'ConfigParser')
def test_missing_project(mock_config, capsys):

    mock_config.return_value = FakeConfig()

    with pytest.raises(SystemExit):
        shell.main(['get', '1', '-p', 'foo'])

    captured = capsys.readouterr()

    assert 'No section for project foo' in captured.err
    assert captured.out == ''


@mock.patch.object(utils.configparser, 'ConfigParser')
@mock.patch.object(shell.os.path, 'exists', new=mock.Mock(return_value=True))
@mock.patch.object(utils, 'migrate_old_config_file')
def test_migrate_config(mock_migrate, mock_config):

    fake_config = FakeConfig(
        {
            'base': {
                'project': 'foo',
                'url': 'https://example.com/',
            },
            'auth': {
                'username': 'user',
                'password': 'pass',
            },
        }
    )
    del fake_config._data['options']
    mock_config.return_value = fake_config

    with pytest.raises(SystemExit):
        shell.main(['get', '1', '-p', 'foo'])

    mock_migrate.assert_called_once_with(mock.ANY, mock_config.return_value)


@mock.patch.object(utils.configparser, 'ConfigParser')
@mock.patch.object(api, 'XMLRPC')
@mock.patch.object(patches, 'action_apply')
def test_server_error(mock_action, mock_api, mock_config, capsys):

    mock_config.return_value = FakeConfig()
    mock_api.side_effect = exceptions.APIError('Unable to connect')

    with pytest.raises(SystemExit):
        shell.main(['get', '1'])

    captured = capsys.readouterr()

    assert 'Unable to connect' in captured.err
    assert captured.out == ''


@mock.patch.object(utils.configparser, 'ConfigParser')
@mock.patch.object(api, 'XMLRPC')
@mock.patch.object(patches, 'action_apply')
def test_apply(mock_action, mock_api, mock_config):

    mock_config.return_value = FakeConfig()
    mock_action.return_value = None

    # test firstly with a single patch ID

    shell.main(['apply', '1'])

    mock_action.assert_called_once_with(mock_api.return_value, 1)
    mock_action.reset_mock()

    # then with multiple patch IDs

    shell.main(['apply', '1', '2', '3'])

    mock_action.assert_has_calls(
        [
            mock.call(mock_api.return_value, 1),
            mock.call(mock_api.return_value, 2),
            mock.call(mock_api.return_value, 3),
        ]
    )


@mock.patch.object(utils.configparser, 'ConfigParser')
@mock.patch.object(api, 'XMLRPC')
@mock.patch.object(patches, 'action_apply')
def test_apply__failed(mock_action, mock_api, mock_config, capsys):

    mock_config.return_value = FakeConfig()
    mock_action.side_effect = [0, 0, 1]

    with pytest.raises(SystemExit):
        shell.main(['apply', '1', '2', '3'])

    captured = capsys.readouterr()

    mock_action.assert_has_calls(
        [
            mock.call(mock_api.return_value, 1),
            mock.call(mock_api.return_value, 2),
            mock.call(mock_api.return_value, 3),
        ]
    )
    assert captured.err == 'Apply failed with exit status 1\n', captured


@mock.patch.object(utils.configparser, 'ConfigParser')
@mock.patch.object(api, 'XMLRPC')
@mock.patch.object(checks, 'action_create')
def test_check_create(mock_action, mock_api, mock_config):

    mock_config.return_value = FakeConfig(
        {
            DEFAULT_PROJECT: {
                'username': 'user',
                'password': 'pass',
            },
        }
    )

    shell.main(
        [
            'check-create',
            '-c',
            'testing',
            '-s',
            'pending',
            '-u',
            'https://example.com/',
            '-d',
            'hello, world',
            '1',
        ]
    )

    mock_action.assert_called_once_with(
        mock_api.return_value,
        1,
        'testing',
        'pending',
        'https://example.com/',
        'hello, world',
    )


@mock.patch.object(utils.configparser, 'ConfigParser')
@mock.patch.object(api, 'XMLRPC')
@mock.patch.object(checks, 'action_create')
def test_check_create__no_auth(
    mock_action,
    mock_api,
    mock_config,
    capsys,
):

    mock_config.return_value = FakeConfig()

    with pytest.raises(SystemExit):
        shell.main(
            [
                'check-create',
                '-c',
                'testing',
                '-s',
                'pending',
                '-u',
                'https://example.com/',
                '-d',
                'hello, world',
                '1',
            ]
        )

    captured = capsys.readouterr()

    mock_action.assert_not_called()
    assert 'The check_create action requires authentication,' in captured.err


@mock.patch.object(utils.configparser, 'ConfigParser')
@mock.patch.object(api, 'XMLRPC')
@mock.patch.object(checks, 'action_info')
def test_check_info(mock_action, mock_api, mock_config):

    mock_config.return_value = FakeConfig()

    shell.main(['check-info', '1', '1'])

    mock_action.assert_called_once_with(mock_api.return_value, 1, 1)


@mock.patch.object(utils.configparser, 'ConfigParser')
@mock.patch.object(api, 'XMLRPC')
@mock.patch.object(checks, 'action_info')
def test_check_info__no_patch_id(mock_action, mock_api, mock_config):

    mock_config.return_value = FakeConfig()

    shell.main(['check-info', '1'])

    mock_action.assert_called_once_with(mock_api.return_value, None, 1)


@mock.patch.object(utils.configparser, 'ConfigParser')
@mock.patch.object(api, 'XMLRPC')
@mock.patch.object(checks, 'action_list')
def test_check_list(mock_action, mock_api, mock_config):

    mock_config.return_value = FakeConfig()

    shell.main(['check-list'])

    mock_action.assert_called_once_with(mock_api.return_value, None, None)


@mock.patch.object(utils.configparser, 'ConfigParser')
@mock.patch.object(api, 'XMLRPC')
@mock.patch.object(patches, 'action_get')
def test_get__numeric_id(mock_action, mock_api, mock_config):

    mock_config.return_value = FakeConfig()
    mock_action.return_value = None

    shell.main(['get', '1'])

    mock_action.assert_called_once_with(mock_api.return_value, 1)


@mock.patch.object(utils.configparser, 'ConfigParser')
@mock.patch.object(api, 'XMLRPC')
@mock.patch.object(patches, 'action_get')
def test_get__multiple_ids(mock_action, mock_api, mock_config):

    mock_config.return_value = FakeConfig()
    mock_action.return_value = None

    shell.main(['get', '1', '2', '3'])

    mock_action.assert_has_calls(
        [
            mock.call(mock_api.return_value, 1),
            mock.call(mock_api.return_value, 2),
            mock.call(mock_api.return_value, 3),
        ]
    )


@mock.patch.object(utils.configparser, 'ConfigParser')
@mock.patch.object(api, 'XMLRPC')
@mock.patch.object(patches, 'patch_id_from_hash')
@mock.patch.object(patches, 'action_get')
def test_get__hash_ids(mock_action, mock_hash, mock_api, mock_config):

    mock_config.return_value = FakeConfig()
    mock_action.return_value = 0
    mock_hash.return_value = 1

    shell.main(['get', '-h', '698fa7f'])

    mock_action.assert_called_once_with(mock_api.return_value, 1)
    mock_hash.assert_called_once_with(
        mock_api.return_value, 'defaultproject', '698fa7f'
    )


@mock.patch.object(utils.configparser, 'ConfigParser')
@mock.patch.object(api, 'XMLRPC')
@mock.patch.object(patches, 'action_get')
def test_get__no_ids(mock_action, mock_api, mock_config, capsys):

    mock_config.return_value = FakeConfig()
    mock_action.return_value = None

    with pytest.raises(SystemExit):
        shell.main(['get'])

    captured = capsys.readouterr()

    assert 'the following arguments are required: PATCH_ID' in captured.err
    assert captured.out == ''


@mock.patch.object(utils.configparser, 'ConfigParser')
@mock.patch.object(api, 'XMLRPC')
@mock.patch.object(patches, 'action_apply')
def test_git_am__no_args(mock_action, mock_api, mock_config):

    mock_config.return_value = FakeConfig()
    mock_action.return_value = 0

    # test firstly with a single patch ID

    shell.main(['git-am', '1'])

    mock_action.assert_called_once_with(
        mock_api.return_value, 1, ['git', 'am']
    )
    mock_action.reset_mock()

    # then with multiple patch IDs

    shell.main(['git-am', '1', '2', '3'])

    mock_action.assert_has_calls(
        [
            mock.call(mock_api.return_value, 1, ['git', 'am']),
            mock.call(mock_api.return_value, 2, ['git', 'am']),
            mock.call(mock_api.return_value, 3, ['git', 'am']),
        ]
    )


@mock.patch.object(utils.configparser, 'ConfigParser')
@mock.patch.object(api, 'XMLRPC')
@mock.patch.object(patches, 'action_apply')
def test_git_am__threeway_option(mock_action, mock_api, mock_config):

    mock_config.return_value = FakeConfig()
    mock_action.return_value = 0

    shell.main(['git-am', '1', '-3'])

    mock_action.assert_called_once_with(
        mock_api.return_value, 1, ['git', 'am', '-3']
    )


@mock.patch.object(utils.configparser, 'ConfigParser')
@mock.patch.object(api, 'XMLRPC')
@mock.patch.object(patches, 'action_apply')
def test_git_am__signoff_option(mock_action, mock_api, mock_config):

    mock_config.return_value = FakeConfig()
    mock_action.return_value = 0

    shell.main(['git-am', '1', '-s'])

    mock_action.assert_called_once_with(
        mock_api.return_value, 1, ['git', 'am', '-s']
    )
    mock_action.reset_mock()


@mock.patch.object(utils.configparser, 'ConfigParser')
@mock.patch.object(api, 'XMLRPC')
@mock.patch.object(patches, 'action_apply')
def test_git_am__threeway_global_conf(mock_action, mock_api, mock_config):

    mock_config.return_value = FakeConfig(
        {
            'options': {
                '3way': True,
            }
        }
    )
    mock_action.return_value = 0

    shell.main(['git-am', '1'])

    mock_action.assert_called_once_with(
        mock_api.return_value, 1, ['git', 'am', '-3']
    )


@mock.patch.object(utils.configparser, 'ConfigParser')
@mock.patch.object(api, 'XMLRPC')
@mock.patch.object(patches, 'action_apply')
def test_git_am__signoff_global_conf(mock_action, mock_api, mock_config):

    mock_config.return_value = FakeConfig(
        {
            'options': {
                'signoff': True,
            }
        }
    )
    mock_action.return_value = 0

    shell.main(['git-am', '1'])

    mock_action.assert_called_once_with(
        mock_api.return_value, 1, ['git', 'am', '-s']
    )
    mock_action.reset_mock()


@mock.patch.object(utils.configparser, 'ConfigParser')
@mock.patch.object(api, 'XMLRPC')
@mock.patch.object(patches, 'action_apply')
def test_git_am__threeway_project_conf(mock_action, mock_api, mock_config):

    mock_config.return_value = FakeConfig(
        {
            DEFAULT_PROJECT: {
                '3way': True,
            }
        }
    )
    mock_action.return_value = 0

    shell.main(['git-am', '1'])

    mock_action.assert_called_once_with(
        mock_api.return_value, 1, ['git', 'am', '-3']
    )


@mock.patch.object(utils.configparser, 'ConfigParser')
@mock.patch.object(api, 'XMLRPC')
@mock.patch.object(patches, 'action_apply')
def test_git_am__signoff_project_conf(mock_action, mock_api, mock_config):

    mock_config.return_value = FakeConfig(
        {
            DEFAULT_PROJECT: {
                'signoff': True,
            }
        }
    )
    mock_action.return_value = 0

    shell.main(['git-am', '1'])

    mock_action.assert_called_once_with(
        mock_api.return_value, 1, ['git', 'am', '-s']
    )
    mock_action.reset_mock()


@mock.patch.object(utils.configparser, 'ConfigParser')
@mock.patch.object(api, 'XMLRPC')
@mock.patch.object(patches, 'action_apply')
def test_git_am__failure(mock_action, mock_api, mock_config, capsys):

    mock_config.return_value = FakeConfig()
    mock_action.return_value = 1

    with pytest.raises(SystemExit):
        shell.main(['git-am', '1'])

    mock_action.assert_called_once_with(
        mock_api.return_value, 1, ['git', 'am']
    )
    mock_action.reset_mock()

    captured = capsys.readouterr()

    assert "'git am' failed with exit status 1\n" in captured.err
    assert captured.out == ''


@mock.patch.object(utils.configparser, 'ConfigParser')
@mock.patch.object(api, 'XMLRPC')
@mock.patch.object(patches, 'action_info')
def test_info(mock_action, mock_api, mock_config):

    mock_config.return_value = FakeConfig()
    mock_action.return_value = None

    # test firstly with a single patch ID

    shell.main(['info', '1'])

    mock_action.assert_called_once_with(mock_api.return_value, 1)
    mock_action.reset_mock()

    # then with multiple patch IDs

    shell.main(['info', '1', '2', '3'])

    mock_action.assert_has_calls(
        [
            mock.call(mock_api.return_value, 1),
            mock.call(mock_api.return_value, 2),
            mock.call(mock_api.return_value, 3),
        ]
    )


@mock.patch.object(utils.configparser, 'ConfigParser')
@mock.patch.object(api, 'XMLRPC')
@mock.patch.object(patches, 'action_list')
def test_list__no_options(mock_action, mock_api, mock_config):

    mock_config.return_value = FakeConfig()

    shell.main(['list'])

    mock_action.assert_called_once_with(
        mock_api.return_value,
        project=DEFAULT_PROJECT,
        submitter=None,
        delegate=None,
        state=None,
        archived=None,
        msgid=None,
        name=None,
        hash=None,
        max_count=None,
        format_str=None,
    )


@mock.patch.object(utils.configparser, 'ConfigParser')
@mock.patch.object(api, 'XMLRPC')
@mock.patch.object(patches, 'action_list')
def test_list__state_filter(mock_action, mock_api, mock_config):

    mock_config.return_value = FakeConfig()

    shell.main(['list', '-s', 'Accepted'])

    mock_action.assert_called_once_with(
        mock_api.return_value,
        project=DEFAULT_PROJECT,
        submitter=None,
        delegate=None,
        state='Accepted',
        archived=None,
        msgid=None,
        name=None,
        hash=None,
        max_count=None,
        format_str=None,
    )


@mock.patch.object(utils.configparser, 'ConfigParser')
@mock.patch.object(api, 'XMLRPC')
@mock.patch.object(patches, 'action_list')
def test_list__archived_filter(mock_action, mock_api, mock_config):

    mock_config.return_value = FakeConfig()

    shell.main(['list', '-a', 'yes'])

    mock_action.assert_called_once_with(
        mock_api.return_value,
        project=DEFAULT_PROJECT,
        submitter=None,
        delegate=None,
        state=None,
        archived=True,
        msgid=None,
        name=None,
        hash=None,
        max_count=None,
        format_str=None,
    )


@mock.patch.object(utils.configparser, 'ConfigParser')
@mock.patch.object(api, 'XMLRPC')
@mock.patch.object(patches, 'action_list')
def test_list__project_filter(mock_action, mock_api, mock_config):

    mock_config.return_value = FakeConfig(
        {
            'fakeproject': {
                'url': 'https://example.com/fakeproject',
            }
        }
    )

    shell.main(['list', '-p', 'fakeproject'])

    mock_action.assert_called_once_with(
        mock_api.return_value,
        project='fakeproject',
        submitter=None,
        delegate=None,
        state=None,
        archived=None,
        msgid=None,
        name=None,
        hash=None,
        max_count=None,
        format_str=None,
    )


@mock.patch.object(utils.configparser, 'ConfigParser')
@mock.patch.object(api, 'XMLRPC')
@mock.patch.object(patches, 'action_list')
def test_list__submitter_filter(mock_action, mock_api, mock_config):

    mock_config.return_value = FakeConfig()

    shell.main(['list', '-w', 'fakesubmitter'])

    mock_action.assert_called_once_with(
        mock_api.return_value,
        project=DEFAULT_PROJECT,
        submitter='fakesubmitter',
        delegate=None,
        state=None,
        archived=None,
        msgid=None,
        name=None,
        hash=None,
        max_count=None,
        format_str=None,
    )


@mock.patch.object(utils.configparser, 'ConfigParser')
@mock.patch.object(api, 'XMLRPC')
@mock.patch.object(patches, 'action_list')
def test_list__delegate_filter(mock_action, mock_api, mock_config):

    mock_config.return_value = FakeConfig()

    shell.main(['list', '-d', 'fakedelegate'])

    mock_action.assert_called_once_with(
        mock_api.return_value,
        project=DEFAULT_PROJECT,
        submitter=None,
        delegate='fakedelegate',
        state=None,
        archived=None,
        msgid=None,
        name=None,
        hash=None,
        max_count=None,
        format_str=None,
    )


@mock.patch.object(utils.configparser, 'ConfigParser')
@mock.patch.object(api, 'XMLRPC')
@mock.patch.object(patches, 'action_list')
def test_list__msgid_filter(mock_action, mock_api, mock_config):

    mock_config.return_value = FakeConfig()

    shell.main(['list', '-m', 'fakemsgid'])

    mock_action.assert_called_once_with(
        mock_api.return_value,
        project=DEFAULT_PROJECT,
        submitter=None,
        delegate=None,
        state=None,
        archived=None,
        msgid='fakemsgid',
        name=None,
        hash=None,
        max_count=None,
        format_str=None,
    )


@mock.patch.object(utils.configparser, 'ConfigParser')
@mock.patch.object(api, 'XMLRPC')
@mock.patch.object(patches, 'action_list')
def test_list__name_filter(mock_action, mock_api, mock_config):

    mock_config.return_value = FakeConfig()

    shell.main(['list', 'fake patch name'])

    mock_action.assert_called_once_with(
        mock_api.return_value,
        project=DEFAULT_PROJECT,
        submitter=None,
        delegate=None,
        state=None,
        archived=None,
        msgid=None,
        name='fake patch name',
        hash=None,
        max_count=None,
        format_str=None,
    )


@mock.patch.object(utils.configparser, 'ConfigParser')
@mock.patch.object(api, 'XMLRPC')
@mock.patch.object(patches, 'action_list')
def test_list__limit_filter(mock_action, mock_api, mock_config):

    mock_config.return_value = FakeConfig()

    shell.main(['list', '-n', '5'])

    mock_action.assert_called_once_with(
        mock_api.return_value,
        project=DEFAULT_PROJECT,
        submitter=None,
        delegate=None,
        state=None,
        archived=None,
        msgid=None,
        name=None,
        hash=None,
        max_count=5,
        format_str=None,
    )


@mock.patch.object(utils.configparser, 'ConfigParser')
@mock.patch.object(api, 'XMLRPC')
@mock.patch.object(patches, 'action_list')
def test_list__limit_reverse_filter(mock_action, mock_api, mock_config):

    mock_config.return_value = FakeConfig()

    shell.main(['list', '-N', '5'])

    mock_action.assert_called_once_with(
        mock_api.return_value,
        project=DEFAULT_PROJECT,
        submitter=None,
        delegate=None,
        state=None,
        archived=None,
        msgid=None,
        name=None,
        hash=None,
        max_count=-5,
        format_str=None,
    )


@mock.patch.object(utils.configparser, 'ConfigParser')
@mock.patch.object(api, 'XMLRPC')
@mock.patch.object(patches, 'action_list')
def test_list__hash_filter(mock_action, mock_api, mock_config):

    mock_config.return_value = FakeConfig()

    shell.main(['list', '-H', '3143a71a9d33f4f12b4469818d205125cace6535'])

    mock_action.assert_called_once_with(
        mock_api.return_value,
        project=DEFAULT_PROJECT,
        submitter=None,
        delegate=None,
        state=None,
        archived=None,
        msgid=None,
        name=None,
        hash='3143a71a9d33f4f12b4469818d205125cace6535',
        max_count=None,
        format_str=None,
    )


@mock.patch.object(utils.configparser, 'ConfigParser')
@mock.patch.object(api, 'XMLRPC')
@mock.patch.object(projects, 'action_list')
def test_projects(mock_action, mock_api, mock_config):

    mock_config.return_value = FakeConfig()

    shell.main(['projects'])

    mock_action.assert_called_once_with(mock_api.return_value)


@mock.patch.object(utils.configparser, 'ConfigParser')
@mock.patch.object(api, 'XMLRPC')
@mock.patch.object(states, 'action_list')
def test_states(mock_action, mock_api, mock_config):

    mock_config.return_value = FakeConfig()

    shell.main(['states'])

    mock_action.assert_called_once_with(mock_api.return_value)


@mock.patch.object(utils.configparser, 'ConfigParser')
@mock.patch.object(api, 'XMLRPC')
@mock.patch.object(patches, 'action_update')
def test_update__no_options(
    mock_action,
    mock_api,
    mock_config,
    capsys,
):

    mock_config.return_value = FakeConfig(
        {
            DEFAULT_PROJECT: {
                'username': 'user',
                'password': 'pass',
            },
        }
    )

    with pytest.raises(SystemExit):
        shell.main(['update', '1'])

    captured = capsys.readouterr()

    assert 'Must specify one or more update options (-a or -s)' in captured.err
    assert captured.out == ''


@mock.patch.object(utils.configparser, 'ConfigParser')
@mock.patch.object(api, 'XMLRPC')
@mock.patch.object(patches, 'action_update')
def test_update__no_auth(
    mock_action,
    mock_api,
    mock_config,
    capsys,
):

    mock_config.return_value = FakeConfig()

    with pytest.raises(SystemExit):
        shell.main(['update', '1', '-a', 'yes'])

    captured = capsys.readouterr()

    mock_action.assert_not_called()
    assert 'The update action requires authentication,' in captured.err


@mock.patch.object(utils.configparser, 'ConfigParser')
@mock.patch.object(api, 'XMLRPC')
@mock.patch.object(patches, 'action_update')
def test_update__state_option(mock_action, mock_api, mock_config):

    mock_config.return_value = FakeConfig(
        {
            DEFAULT_PROJECT: {
                'username': 'user',
                'password': 'pass',
            },
        }
    )

    shell.main(['update', '1', '-s', 'Accepted'])

    mock_action.assert_called_once_with(
        mock_api.return_value,
        1,
        state='Accepted',
        archived=None,
        commit_ref=None,
    )


@mock.patch.object(utils.configparser, 'ConfigParser')
@mock.patch.object(api, 'XMLRPC')
@mock.patch.object(patches, 'action_update')
def test_update__archive_option(mock_action, mock_api, mock_config):

    mock_config.return_value = FakeConfig(
        {
            DEFAULT_PROJECT: {
                'username': 'user',
                'password': 'pass',
            },
        }
    )

    shell.main(['update', '1', '-a', 'yes'])

    mock_action.assert_called_once_with(
        mock_api.return_value, 1, state=None, archived='yes', commit_ref=None
    )


@mock.patch.object(utils.configparser, 'ConfigParser')
@mock.patch.object(api, 'XMLRPC')
@mock.patch.object(patches, 'action_update')
def test_update__commitref_option(mock_action, mock_api, mock_config):

    mock_config.return_value = FakeConfig(
        {
            DEFAULT_PROJECT: {
                'username': 'user',
                'password': 'pass',
            },
        }
    )

    shell.main(['update', '1', '-s', 'Accepted', '-c', '698fa7f'])

    mock_action.assert_called_once_with(
        mock_api.return_value,
        1,
        state='Accepted',
        archived=None,
        commit_ref='698fa7f',
    )


@mock.patch.object(utils.configparser, 'ConfigParser')
@mock.patch.object(api, 'XMLRPC')
@mock.patch.object(patches, 'action_update')
def test_update__commitref_with_multiple_patches(
    mock_action,
    mock_api,
    mock_config,
    capsys,
):

    mock_config.return_value = FakeConfig(
        {
            DEFAULT_PROJECT: {
                'username': 'user',
                'password': 'pass',
            },
        }
    )

    with pytest.raises(SystemExit):
        shell.main(['update', '-s', 'Accepted', '-c', '698fa7f', '1', '2'])

    captured = capsys.readouterr()

    mock_action.assert_not_called()
    assert 'Declining update with COMMIT-REF on multiple IDs' in captured.err


@mock.patch.object(patches, 'action_view')
@mock.patch.object(utils.configparser, 'ConfigParser')
@mock.patch.object(api, 'XMLRPC')
def test_view(mock_api, mock_config, mock_view, capsys):

    fake_config = FakeConfig()

    mock_config.return_value = fake_config
    mock_api.return_value.patch_get_mbox.return_value = 'foo'

    # test firstly with a single patch ID

    shell.main(['view', '1'])

    mock_view.assert_called_once_with(mock_api.return_value, [1])
