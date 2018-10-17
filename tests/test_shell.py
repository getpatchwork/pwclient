import mock
import pytest

from pwclient import projects
from pwclient import shell
from pwclient import xmlrpc

from . import fakes


DEFAULT_PROJECT = 'defaultproject'


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
            raise shell.ConfigParser.NoSectionError(section)

        self._data[section][option] = value

    def get(self, section, option):
        if section not in self._data:
            raise shell.ConfigParser.NoSectionError(section)

        if option not in self._data[section]:
            raise shell.ConfigParser.NoOptionError(section, option)

        return self._data[section][option]

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


@mock.patch.object(shell.ConfigParser, 'ConfigParser')
def test_no_project(mock_config, capsys):
    fake_config = FakeConfig()
    del fake_config._data['options']['default']

    mock_config.return_value = fake_config

    with pytest.raises(SystemExit):
        shell.main(['get', '1'])

    captured = capsys.readouterr()

    assert 'No default project configured' in captured.err
    assert captured.out == ''


@mock.patch.object(shell.ConfigParser, 'ConfigParser')
def test_no_project_url(mock_config, capsys):
    fake_config = FakeConfig()
    del fake_config._data[DEFAULT_PROJECT]['url']

    mock_config.return_value = fake_config

    with pytest.raises(SystemExit):
        shell.main(['get', '1'])

    captured = capsys.readouterr()

    assert 'No URL for project %s' % DEFAULT_PROJECT in captured.err
    assert captured.out == ''


@mock.patch.object(shell.ConfigParser, 'ConfigParser')
def test_missing_project(mock_config, capsys):

    mock_config.return_value = FakeConfig()

    with pytest.raises(SystemExit):
        shell.main(['get', '1', '-p', 'foo'])

    captured = capsys.readouterr()

    assert 'No section for project foo' in captured.err
    assert captured.out == ''


@mock.patch.object(shell.ConfigParser, 'ConfigParser')
@mock.patch.object(shell.os.path, 'exists', new=mock.Mock(return_value=True))
@mock.patch.object(shell.shutil, 'copy2', new=mock.Mock())
@mock.patch.object(shell, 'open', new_callable=mock.mock_open, read_data='1')
def test_migrate_config(mock_open, mock_config, capsys):

    fake_config = FakeConfig({
        'base': {
            'project': 'foo',
            'url': 'https://example.com/',
        },
        'auth': {
            'username': 'user',
            'password': 'pass',
        },
    })
    del fake_config._data['options']
    mock_config.return_value = fake_config

    with pytest.raises(SystemExit):
        shell.main(['get', '1', '-p', 'foo'])

    captured = capsys.readouterr()

    assert 'is in the old format. Migrating it...' in captured.err
    assert captured.out == ''


@mock.patch.object(shell.ConfigParser, 'ConfigParser')
@mock.patch.object(xmlrpc.xmlrpclib, 'Server')
@mock.patch.object(shell, 'action_apply')
@mock.patch.object(xmlrpc, 'Transport', new=mock.Mock())
def test_server_error(mock_action, mock_server, mock_config, capsys):

    mock_config.return_value = FakeConfig()
    mock_server.side_effect = IOError('foo')

    with pytest.raises(SystemExit):
        shell.main(['get', '1'])

    captured = capsys.readouterr()

    assert 'Unable to connect' in captured.err
    assert captured.out == ''


@mock.patch.object(shell.ConfigParser, 'ConfigParser')
@mock.patch.object(xmlrpc.xmlrpclib, 'Server')
@mock.patch.object(shell, 'action_apply')
@mock.patch.object(xmlrpc, 'Transport', new=mock.Mock())
def test_apply(mock_action, mock_server, mock_config):

    mock_config.return_value = FakeConfig()
    mock_action.return_value = None

    # test firstly with a single patch ID

    shell.main(['apply', '1'])

    mock_action.assert_called_once_with(mock_server.return_value, 1)
    mock_action.reset_mock()

    # then with multiple patch IDs

    shell.main(['apply', '1', '2', '3'])

    mock_action.assert_has_calls([
        mock.call(mock_server.return_value, 1),
        mock.call(mock_server.return_value, 2),
        mock.call(mock_server.return_value, 3),
    ])


@mock.patch.object(shell.ConfigParser, 'ConfigParser')
@mock.patch.object(xmlrpc.xmlrpclib, 'Server')
@mock.patch.object(shell, 'action_apply')
@mock.patch.object(xmlrpc, 'Transport', new=mock.Mock())
def test_apply__failed(mock_action, mock_server, mock_config, capsys):

    mock_config.return_value = FakeConfig()
    mock_action.side_effect = [0, 0, 1]

    with pytest.raises(SystemExit):
        shell.main(['apply', '1', '2', '3'])

    captured = capsys.readouterr()

    mock_action.assert_has_calls([
        mock.call(mock_server.return_value, 1),
        mock.call(mock_server.return_value, 2),
        mock.call(mock_server.return_value, 3),
    ])
    assert captured.err == 'Apply failed with exit status 1\n', captured


@mock.patch.object(shell.ConfigParser, 'ConfigParser')
@mock.patch.object(xmlrpc.xmlrpclib, 'Server')
@mock.patch.object(shell, 'action_check_create')
@mock.patch.object(xmlrpc, 'Transport')
def test_check_create(mock_transport, mock_action, mock_server, mock_config):

    mock_config.return_value = FakeConfig({
        DEFAULT_PROJECT: {
            'username': 'user',
            'password': 'pass',
        },
    })

    shell.main(['check-create', '-c', 'testing', '-s', 'pending',
                '-u', 'https://example.com/', '-d', 'hello, world', '1'])

    mock_action.assert_called_once_with(
        mock_server.return_value, 1, 'testing', 'pending',
        'https://example.com/', 'hello, world')
    mock_transport.return_value.set_credentials.assert_called_once_with(
        'user', 'pass')


@mock.patch.object(shell.ConfigParser, 'ConfigParser')
@mock.patch.object(xmlrpc.xmlrpclib, 'Server')
@mock.patch.object(shell, 'action_check_create')
@mock.patch.object(xmlrpc, 'Transport')
def test_check_create__no_auth(
        mock_transport, mock_action, mock_server, mock_config, capsys):

    mock_config.return_value = FakeConfig()

    with pytest.raises(SystemExit):
        shell.main(['check-create', '-c', 'testing', '-s', 'pending',
                    '-u', 'https://example.com/', '-d', 'hello, world', '1'])

    captured = capsys.readouterr()

    mock_action.assert_not_called()
    mock_transport.return_value.set_credentials.assert_not_called()
    assert 'The check_create action requires authentication,' in captured.err


@mock.patch.object(shell.ConfigParser, 'ConfigParser')
@mock.patch.object(xmlrpc.xmlrpclib, 'Server')
@mock.patch.object(shell, 'action_check_info')
@mock.patch.object(xmlrpc, 'Transport', new=mock.Mock())
def test_check_info(mock_action, mock_server, mock_config):

    mock_config.return_value = FakeConfig()

    shell.main(['check-info', '1'])

    mock_action.assert_called_once_with(mock_server.return_value, 1)


@mock.patch.object(shell.ConfigParser, 'ConfigParser')
@mock.patch.object(xmlrpc.xmlrpclib, 'Server')
@mock.patch.object(shell, 'action_check_list')
@mock.patch.object(xmlrpc, 'Transport', new=mock.Mock())
def test_check_list(mock_action, mock_server, mock_config):

    mock_config.return_value = FakeConfig()

    shell.main(['check-list'])

    mock_action.assert_called_once_with(mock_server.return_value)


@mock.patch.object(shell.ConfigParser, 'ConfigParser')
@mock.patch.object(xmlrpc.xmlrpclib, 'Server')
@mock.patch.object(shell, 'action_get')
@mock.patch.object(xmlrpc, 'Transport', new=mock.Mock())
def test_get__numeric_id(mock_action, mock_server, mock_config):

    mock_config.return_value = FakeConfig()
    mock_action.return_value = None

    shell.main(['get', '1'])

    mock_action.assert_called_once_with(mock_server.return_value, 1)


@mock.patch.object(shell.ConfigParser, 'ConfigParser')
@mock.patch.object(xmlrpc.xmlrpclib, 'Server')
@mock.patch.object(shell, 'action_get')
@mock.patch.object(xmlrpc, 'Transport', new=mock.Mock())
def test_get__multiple_ids(mock_action, mock_server, mock_config):

    mock_config.return_value = FakeConfig()
    mock_action.return_value = None

    shell.main(['get', '1', '2', '3'])

    mock_action.assert_has_calls([
        mock.call(mock_server.return_value, 1),
        mock.call(mock_server.return_value, 2),
        mock.call(mock_server.return_value, 3),
    ])


@mock.patch.object(shell.ConfigParser, 'ConfigParser')
@mock.patch.object(xmlrpc.xmlrpclib, 'Server')
@mock.patch.object(shell, 'patch_id_from_hash')
@mock.patch.object(shell, 'action_get')
@mock.patch.object(xmlrpc, 'Transport', new=mock.Mock())
def test_get__hash_ids(mock_action, mock_hash, mock_server, mock_config):

    mock_config.return_value = FakeConfig()
    mock_action.return_value = 0
    mock_hash.return_value = 1

    shell.main(['get', '-h', '698fa7f'])

    mock_action.assert_called_once_with(mock_server.return_value, 1)
    mock_hash.assert_called_once_with(
        mock_server.return_value, 'defaultproject', '698fa7f')


@mock.patch.object(shell.ConfigParser, 'ConfigParser')
@mock.patch.object(xmlrpc.xmlrpclib, 'Server')
@mock.patch.object(shell, 'action_get')
@mock.patch.object(xmlrpc, 'Transport', new=mock.Mock())
def test_get__no_ids(mock_action, mock_server, mock_config, capsys):

    mock_config.return_value = FakeConfig()
    mock_action.return_value = None

    with pytest.raises(SystemExit):
        shell.main(['get'])

    captured = capsys.readouterr()

    assert 'pwclient get: error: too few arguments' in captured.err
    assert captured.out == ''


@mock.patch.object(shell.ConfigParser, 'ConfigParser')
@mock.patch.object(xmlrpc.xmlrpclib, 'Server')
@mock.patch.object(shell, 'action_apply')
@mock.patch.object(xmlrpc, 'Transport', new=mock.Mock())
def test_git_am__no_args(mock_action, mock_server, mock_config):

    mock_config.return_value = FakeConfig()
    mock_action.return_value = 0

    # test firstly with a single patch ID

    shell.main(['git-am', '1'])

    mock_action.assert_called_once_with(
        mock_server.return_value, 1, ['git', 'am'])
    mock_action.reset_mock()

    # then with multiple patch IDs

    shell.main(['git-am', '1', '2', '3'])

    mock_action.assert_has_calls([
        mock.call(mock_server.return_value, 1, ['git', 'am']),
        mock.call(mock_server.return_value, 2, ['git', 'am']),
        mock.call(mock_server.return_value, 3, ['git', 'am']),
    ])


@mock.patch.object(shell.ConfigParser, 'ConfigParser')
@mock.patch.object(xmlrpc.xmlrpclib, 'Server')
@mock.patch.object(shell, 'action_apply')
@mock.patch.object(xmlrpc, 'Transport', new=mock.Mock())
def test_git_am__threeway_option(mock_action, mock_server, mock_config):

    mock_config.return_value = FakeConfig()
    mock_action.return_value = 0

    shell.main(['git-am', '1', '-3'])

    mock_action.assert_called_once_with(
        mock_server.return_value, 1, ['git', 'am', '-3'])


@mock.patch.object(shell.ConfigParser, 'ConfigParser')
@mock.patch.object(xmlrpc.xmlrpclib, 'Server')
@mock.patch.object(shell, 'action_apply')
@mock.patch.object(xmlrpc, 'Transport', new=mock.Mock())
def test_git_am__signoff_option(mock_action, mock_server, mock_config):

    mock_config.return_value = FakeConfig()
    mock_action.return_value = 0

    shell.main(['git-am', '1', '-s'])

    mock_action.assert_called_once_with(
        mock_server.return_value, 1, ['git', 'am', '-s'])
    mock_action.reset_mock()


@mock.patch.object(shell.ConfigParser, 'ConfigParser')
@mock.patch.object(xmlrpc.xmlrpclib, 'Server')
@mock.patch.object(shell, 'action_apply')
@mock.patch.object(xmlrpc, 'Transport', new=mock.Mock())
def test_git_am__threeway_global_conf(mock_action, mock_server, mock_config):

    mock_config.return_value = FakeConfig({
        'options': {
            '3way': True,
        }
    })
    mock_action.return_value = 0

    shell.main(['git-am', '1'])

    mock_action.assert_called_once_with(
        mock_server.return_value, 1, ['git', 'am', '-3'])


@mock.patch.object(shell.ConfigParser, 'ConfigParser')
@mock.patch.object(xmlrpc.xmlrpclib, 'Server')
@mock.patch.object(shell, 'action_apply')
@mock.patch.object(xmlrpc, 'Transport', new=mock.Mock())
def test_git_am__signoff_global_conf(mock_action, mock_server, mock_config):

    mock_config.return_value = FakeConfig({
        'options': {
            'signoff': True,
        }
    })
    mock_action.return_value = 0

    shell.main(['git-am', '1'])

    mock_action.assert_called_once_with(
        mock_server.return_value, 1, ['git', 'am', '-s'])
    mock_action.reset_mock()


@mock.patch.object(shell.ConfigParser, 'ConfigParser')
@mock.patch.object(xmlrpc.xmlrpclib, 'Server')
@mock.patch.object(shell, 'action_apply')
@mock.patch.object(xmlrpc, 'Transport', new=mock.Mock())
def test_git_am__threeway_project_conf(mock_action, mock_server, mock_config):

    mock_config.return_value = FakeConfig({
        DEFAULT_PROJECT: {
            '3way': True,
        }
    })
    mock_action.return_value = 0

    shell.main(['git-am', '1'])

    mock_action.assert_called_once_with(
        mock_server.return_value, 1, ['git', 'am', '-3'])


@mock.patch.object(shell.ConfigParser, 'ConfigParser')
@mock.patch.object(xmlrpc.xmlrpclib, 'Server')
@mock.patch.object(shell, 'action_apply')
@mock.patch.object(xmlrpc, 'Transport', new=mock.Mock())
def test_git_am__signoff_project_conf(mock_action, mock_server, mock_config):

    mock_config.return_value = FakeConfig({
        DEFAULT_PROJECT: {
            'signoff': True,
        }
    })
    mock_action.return_value = 0

    shell.main(['git-am', '1'])

    mock_action.assert_called_once_with(
        mock_server.return_value, 1, ['git', 'am', '-s'])
    mock_action.reset_mock()


@mock.patch.object(shell.ConfigParser, 'ConfigParser')
@mock.patch.object(xmlrpc.xmlrpclib, 'Server')
@mock.patch.object(shell, 'action_apply')
@mock.patch.object(xmlrpc, 'Transport', new=mock.Mock())
def test_git_am__failure(mock_action, mock_server, mock_config, capsys):

    mock_config.return_value = FakeConfig()
    mock_action.return_value = 1

    with pytest.raises(SystemExit):
        shell.main(['git-am', '1'])

    mock_action.assert_called_once_with(
        mock_server.return_value, 1, ['git', 'am'])
    mock_action.reset_mock()

    captured = capsys.readouterr()

    assert "'git am' failed with exit status 1\n" in captured.err
    assert captured.out == ''


@mock.patch.object(shell.ConfigParser, 'ConfigParser')
@mock.patch.object(xmlrpc.xmlrpclib, 'Server')
@mock.patch.object(shell, 'action_info')
@mock.patch.object(xmlrpc, 'Transport', new=mock.Mock())
def test_info(mock_action, mock_server, mock_config):

    mock_config.return_value = FakeConfig()
    mock_action.return_value = None

    # test firstly with a single patch ID

    shell.main(['info', '1'])

    mock_action.assert_called_once_with(mock_server.return_value, 1)
    mock_action.reset_mock()

    # then with multiple patch IDs

    shell.main(['info', '1', '2', '3'])

    mock_action.assert_has_calls([
        mock.call(mock_server.return_value, 1),
        mock.call(mock_server.return_value, 2),
        mock.call(mock_server.return_value, 3),
    ])


@mock.patch.object(shell.ConfigParser, 'ConfigParser')
@mock.patch.object(xmlrpc.xmlrpclib, 'Server')
@mock.patch.object(shell, 'Filter')
@mock.patch.object(shell, 'action_list')
@mock.patch.object(xmlrpc, 'Transport', new=mock.Mock())
def test_list__no_options(mock_action, mock_filter, mock_server, mock_config):

    mock_config.return_value = FakeConfig()

    shell.main(['list'])

    mock_action.assert_called_once_with(
        mock_server.return_value, mock_filter.return_value, None, None, None)
    assert mock_filter.return_value.add.mock_calls == [
        mock.call('project', mock.ANY),
    ]


@mock.patch.object(shell.ConfigParser, 'ConfigParser')
@mock.patch.object(xmlrpc.xmlrpclib, 'Server')
@mock.patch.object(shell, 'Filter')
@mock.patch.object(shell, 'action_list')
@mock.patch.object(xmlrpc, 'Transport', new=mock.Mock())
def test_list__state_filter(
        mock_action, mock_filter, mock_server, mock_config):

    mock_config.return_value = FakeConfig()

    shell.main(['list', '-s', 'Accepted'])

    mock_action.assert_called_once_with(
        mock_server.return_value, mock_filter.return_value, None, None, None)
    assert mock_filter.return_value.add.mock_calls == [
        mock.call('project', mock.ANY),
        mock.call('state', 'Accepted'),
    ]


@mock.patch.object(shell.ConfigParser, 'ConfigParser')
@mock.patch.object(xmlrpc.xmlrpclib, 'Server')
@mock.patch.object(shell, 'Filter')
@mock.patch.object(shell, 'action_list')
@mock.patch.object(xmlrpc, 'Transport', new=mock.Mock())
def test_list__archived_filter(
        mock_action, mock_filter, mock_server, mock_config):

    mock_config.return_value = FakeConfig()

    shell.main(['list', '-a', 'yes'])

    mock_action.assert_called_once_with(
        mock_server.return_value, mock_filter.return_value, None, None, None)
    assert mock_filter.return_value.add.mock_calls == [
        mock.call('project', mock.ANY),
        mock.call('archived', True),
    ]


@mock.patch.object(shell.ConfigParser, 'ConfigParser')
@mock.patch.object(xmlrpc.xmlrpclib, 'Server')
@mock.patch.object(shell, 'Filter')
@mock.patch.object(shell, 'action_list')
@mock.patch.object(xmlrpc, 'Transport', new=mock.Mock())
def test_list__project_filter(
        mock_action, mock_filter, mock_server, mock_config):

    mock_config.return_value = FakeConfig({
        'fakeproject': {
            'url': 'https://example.com/fakeproject',
        }
    })

    shell.main(['list', '-p', 'fakeproject'])

    mock_action.assert_called_once_with(
        mock_server.return_value, mock_filter.return_value, None, None, None)
    assert mock_filter.return_value.add.mock_calls == [
        mock.call('project', 'fakeproject'),
    ]


@mock.patch.object(shell.ConfigParser, 'ConfigParser')
@mock.patch.object(xmlrpc.xmlrpclib, 'Server')
@mock.patch.object(shell, 'Filter')
@mock.patch.object(shell, 'action_list')
@mock.patch.object(xmlrpc, 'Transport', new=mock.Mock())
def test_list__submitter_filter(
        mock_action, mock_filter, mock_server, mock_config):

    mock_config.return_value = FakeConfig()

    shell.main(['list', '-w', 'fakesubmitter'])

    mock_action.assert_called_once_with(
        mock_server.return_value, mock_filter.return_value, 'fakesubmitter',
        None, None)
    assert mock_filter.return_value.add.mock_calls == [
        mock.call('project', mock.ANY),
    ]


@mock.patch.object(shell.ConfigParser, 'ConfigParser')
@mock.patch.object(xmlrpc.xmlrpclib, 'Server')
@mock.patch.object(shell, 'Filter')
@mock.patch.object(shell, 'action_list')
@mock.patch.object(xmlrpc, 'Transport', new=mock.Mock())
def test_list__delegate_filter(
        mock_action, mock_filter, mock_server, mock_config):

    mock_config.return_value = FakeConfig()

    shell.main(['list', '-d', 'fakedelegate'])

    mock_action.assert_called_once_with(
        mock_server.return_value, mock_filter.return_value, None,
        'fakedelegate', None)
    assert mock_filter.return_value.add.mock_calls == [
        mock.call('project', mock.ANY),
    ]


@mock.patch.object(shell.ConfigParser, 'ConfigParser')
@mock.patch.object(xmlrpc.xmlrpclib, 'Server')
@mock.patch.object(shell, 'Filter')
@mock.patch.object(shell, 'action_list')
@mock.patch.object(xmlrpc, 'Transport', new=mock.Mock())
def test_list__msgid_filter(
        mock_action, mock_filter, mock_server, mock_config):

    mock_config.return_value = FakeConfig()

    shell.main(['list', '-m', 'fakemsgid'])

    mock_action.assert_called_once_with(
        mock_server.return_value, mock_filter.return_value, None, None, None)
    assert mock_filter.return_value.add.mock_calls == [
        mock.call('project', mock.ANY),
        mock.call('msgid', 'fakemsgid'),
    ]


@mock.patch.object(shell.ConfigParser, 'ConfigParser')
@mock.patch.object(xmlrpc.xmlrpclib, 'Server')
@mock.patch.object(shell, 'Filter')
@mock.patch.object(shell, 'action_list')
@mock.patch.object(xmlrpc, 'Transport', new=mock.Mock())
def test_list__name_filter(
        mock_action, mock_filter, mock_server, mock_config):

    mock_config.return_value = FakeConfig()

    shell.main(['list', 'fake patch name'])

    mock_action.assert_called_once_with(
        mock_server.return_value, mock_filter.return_value, None, None, None)
    assert mock_filter.return_value.add.mock_calls == [
        mock.call('project', mock.ANY),
        mock.call('name__icontains', 'fake patch name'),
    ]


@mock.patch.object(shell.ConfigParser, 'ConfigParser')
@mock.patch.object(xmlrpc.xmlrpclib, 'Server')
@mock.patch.object(shell, 'Filter')
@mock.patch.object(shell, 'action_list')
@mock.patch.object(xmlrpc, 'Transport', new=mock.Mock())
def test_list__limit_filter(
        mock_action, mock_filter, mock_server, mock_config):

    mock_config.return_value = FakeConfig()

    shell.main(['list', '-n', '5'])

    mock_action.assert_called_once_with(
        mock_server.return_value, mock_filter.return_value, None, None, None)
    assert mock_filter.return_value.add.mock_calls == [
        mock.call('max_count', 5),
        mock.call('project', mock.ANY),
    ]


@mock.patch.object(shell.ConfigParser, 'ConfigParser')
@mock.patch.object(xmlrpc.xmlrpclib, 'Server')
@mock.patch.object(shell, 'Filter')
@mock.patch.object(shell, 'action_list')
@mock.patch.object(xmlrpc, 'Transport', new=mock.Mock())
def test_list__limit_reverse_filter(
        mock_action, mock_filter, mock_server, mock_config):

    mock_config.return_value = FakeConfig()

    shell.main(['list', '-N', '5'])

    mock_action.assert_called_once_with(
        mock_server.return_value, mock_filter.return_value, None, None, None)
    assert mock_filter.return_value.add.mock_calls == [
        mock.call('max_count', -5),
        mock.call('project', mock.ANY),
    ]


@mock.patch.object(shell.ConfigParser, 'ConfigParser')
@mock.patch.object(xmlrpc.xmlrpclib, 'Server')
@mock.patch.object(projects, 'action_list')
@mock.patch.object(xmlrpc, 'Transport', new=mock.Mock())
def test_projects(mock_action, mock_server, mock_config):

    mock_config.return_value = FakeConfig()

    shell.main(['projects'])

    mock_action.assert_called_once_with(mock_server.return_value)


@mock.patch.object(shell.ConfigParser, 'ConfigParser')
@mock.patch.object(xmlrpc.xmlrpclib, 'Server')
@mock.patch.object(shell, 'action_states')
@mock.patch.object(xmlrpc, 'Transport', new=mock.Mock())
def test_states(mock_action, mock_server, mock_config):

    mock_config.return_value = FakeConfig()

    shell.main(['states'])

    mock_action.assert_called_once_with(mock_server.return_value)


def test_update__no_options(capsys):
    with pytest.raises(SystemExit):
        shell.main(['update', '1'])

    captured = capsys.readouterr()

    assert 'Must specify one or more update options (-a or -s)' in captured.err
    assert captured.out == ''


@mock.patch.object(shell.ConfigParser, 'ConfigParser')
@mock.patch.object(xmlrpc.xmlrpclib, 'Server')
@mock.patch.object(shell, 'action_update_patch')
@mock.patch.object(xmlrpc, 'Transport')
def test_update__no_auth(
        mock_transport, mock_action, mock_server, mock_config, capsys):

    mock_config.return_value = FakeConfig()

    with pytest.raises(SystemExit):
        shell.main(['update', '1', '-a', 'yes'])

    captured = capsys.readouterr()

    mock_action.assert_not_called()
    mock_transport.return_value.set_credentials.assert_not_called()
    assert 'The update action requires authentication,' in captured.err


@mock.patch.object(shell.ConfigParser, 'ConfigParser')
@mock.patch.object(xmlrpc.xmlrpclib, 'Server')
@mock.patch.object(shell, 'action_update_patch')
@mock.patch.object(xmlrpc, 'Transport')
def test_update__state_option(
        mock_transport, mock_action, mock_server, mock_config):

    mock_config.return_value = FakeConfig({
        DEFAULT_PROJECT: {
            'username': 'user',
            'password': 'pass',
        },
    })

    shell.main(['update', '1', '-s', 'Accepted'])

    mock_action.assert_called_once_with(
        mock_server.return_value, 1, state='Accepted', archived=None,
        commit=None)
    mock_transport.return_value.set_credentials.assert_called_once_with(
        'user', 'pass')


@mock.patch.object(shell.ConfigParser, 'ConfigParser')
@mock.patch.object(xmlrpc.xmlrpclib, 'Server')
@mock.patch.object(shell, 'action_update_patch')
@mock.patch.object(xmlrpc, 'Transport')
def test_update__archive_option(
        mock_transport, mock_action, mock_server, mock_config):

    mock_config.return_value = FakeConfig({
        DEFAULT_PROJECT: {
            'username': 'user',
            'password': 'pass',
        },
    })

    shell.main(['update', '1', '-a', 'yes'])

    mock_action.assert_called_once_with(
        mock_server.return_value, 1, state=None, archived='yes',
        commit=None)
    mock_transport.return_value.set_credentials.assert_called_once_with(
        'user', 'pass')


@mock.patch.object(shell.ConfigParser, 'ConfigParser')
@mock.patch.object(xmlrpc.xmlrpclib, 'Server')
@mock.patch.object(shell, 'action_update_patch')
@mock.patch.object(xmlrpc, 'Transport')
def test_update__commitref_option(
        mock_transport, mock_action, mock_server, mock_config):

    mock_config.return_value = FakeConfig({
        DEFAULT_PROJECT: {
            'username': 'user',
            'password': 'pass',
        },
    })

    shell.main(['update', '1', '-s', 'Accepted', '-c', '698fa7f'])

    mock_action.assert_called_once_with(
        mock_server.return_value, 1, state='Accepted', archived=None,
        commit='698fa7f')
    mock_transport.return_value.set_credentials.assert_called_once_with(
        'user', 'pass')


@mock.patch.object(shell.ConfigParser, 'ConfigParser')
@mock.patch.object(xmlrpc.xmlrpclib, 'Server')
@mock.patch.object(shell, 'action_update_patch')
@mock.patch.object(xmlrpc, 'Transport')
def test_update__commitref_with_multiple_patches(
        mock_transport, mock_action, mock_server, mock_config, capsys):

    mock_config.return_value = FakeConfig({
        DEFAULT_PROJECT: {
            'username': 'user',
            'password': 'pass',
        },
    })

    with pytest.raises(SystemExit):
        shell.main(['update', '-s', 'Accepted', '-c', '698fa7f', '1', '2'])

    captured = capsys.readouterr()

    mock_action.assert_not_called()
    mock_transport.return_value.set_credentials.assert_not_called()
    assert 'Declining update with COMMIT-REF on multiple IDs' in captured.err


@mock.patch.object(shell.os.environ, 'get')
@mock.patch.object(shell.subprocess, 'Popen')
@mock.patch.object(shell.ConfigParser, 'ConfigParser')
@mock.patch.object(xmlrpc.xmlrpclib, 'Server')
@mock.patch.object(xmlrpc, 'Transport', new=mock.Mock())
def test_view__no_pager(
        mock_server, mock_config, mock_popen, mock_env, capsys):

    fake_config = FakeConfig()

    mock_env.return_value = None
    mock_config.return_value = fake_config
    mock_server.return_value.patch_get_mbox.return_value = 'foo'

    # test firstly with a single patch ID

    shell.main(['view', '1'])

    captured = capsys.readouterr()

    mock_popen.assert_not_called()
    mock_server.return_value.patch_get_mbox.assert_has_calls([
        mock.call(1),
    ])

    assert captured.out == 'foo\n'

    # then with multiple patch IDs

    mock_server.reset_mock()
    mock_server.return_value.patch_get_mbox.side_effect = [
        'foo', 'bar', 'baz'
    ]

    shell.main(['view', '1', '2', '3'])

    captured = capsys.readouterr()

    mock_popen.assert_not_called()
    mock_server.return_value.patch_get_mbox.assert_has_calls([
        mock.call(1),
        mock.call(2),
        mock.call(3),
    ])
    assert captured.out == 'foo\nbar\nbaz\n'


@mock.patch.object(shell.os.environ, 'get')
@mock.patch.object(shell.subprocess, 'Popen')
@mock.patch.object(shell.ConfigParser, 'ConfigParser')
@mock.patch.object(xmlrpc.xmlrpclib, 'Server')
@mock.patch.object(xmlrpc, 'Transport', new=mock.Mock())
def test_view__with_pager(
        mock_server, mock_config, mock_popen, mock_env, capsys):

    fake_config = FakeConfig()

    mock_env.return_value = 'less'
    mock_config.return_value = fake_config
    mock_server.return_value.patch_get_mbox.return_value = 'foo'

    # test firstly with a single patch ID

    shell.main(['view', '1'])

    captured = capsys.readouterr()

    mock_popen.assert_called_once_with(['less'], stdin=mock.ANY)
    mock_popen.return_value.communicate.assert_has_calls([
        mock.call(input=b'foo'),
    ])
    mock_server.return_value.patch_get_mbox.assert_has_calls([
        mock.call(1),
    ])

    assert captured.out == ''

    # then with multiple patch IDs

    mock_popen.reset_mock()
    mock_server.reset_mock()
    mock_server.return_value.patch_get_mbox.side_effect = [
        'foo', 'bar', 'baz'
    ]

    shell.main(['view', '1', '2', '3'])

    captured = capsys.readouterr()

    mock_popen.assert_called_once_with(['less'], stdin=mock.ANY)
    mock_popen.return_value.communicate.assert_has_calls([
        mock.call(input=b'foo\nbar\nbaz'),
    ])
    mock_server.return_value.patch_get_mbox.assert_has_calls([
        mock.call(1),
        mock.call(2),
        mock.call(3),
    ])
    assert captured.out == ''


def test_state_id_by_name__empty_name():
    rpc = mock.Mock()

    result = shell.state_id_by_name(rpc, '')

    assert result == 0
    rpc.state_list.assert_not_called()


def test_state_id_by_name__no_matches():
    rpc = mock.Mock()
    rpc.state_list.return_value = [
        {'id': 1, 'name': 'bar'},
        {'id': 2, 'name': 'baz'},
    ]

    result = shell.state_id_by_name(rpc, 'foo')

    assert result == 0
    rpc.state_list.assert_called_once_with('foo', 0)


def test_state_id_by_name():
    rpc = mock.Mock()
    rpc.state_list.return_value = [
        {'id': 1, 'name': 'bar'},
        {'id': 2, 'name': 'baz'},
        {'id': 3, 'name': 'foo'},
    ]

    result = shell.state_id_by_name(rpc, 'foo')

    assert result == 3
    rpc.state_list.assert_called_once_with('foo', 0)


def test_person_ids_by_name__empty_name():
    rpc = mock.Mock()

    result = shell.person_ids_by_name(rpc, '')

    assert result == []
    rpc.person_list.assert_not_called()


def test_person_ids_by_name__no_matches():
    rpc = mock.Mock()
    rpc.person_list.return_value = []

    result = shell.person_ids_by_name(rpc, 'foo')

    assert result == []
    rpc.person_list.assert_called_once_with('foo', 0)


def test_person_ids_by_name():
    rpc = mock.Mock()
    rpc.person_list.return_value = [
        {'id': 3, 'name': 'foo'},
        {'id': 35, 'name': 'foobar'},
    ]

    result = shell.person_ids_by_name(rpc, 'foo')

    assert result == [3, 35]
    rpc.person_list.assert_called_once_with('foo', 0)


def test_patch_id_from_hash__no_matches(capsys):
    rpc = mock.Mock()
    rpc.patch_get_by_project_hash.return_value = {}

    with pytest.raises(SystemExit):
        shell.patch_id_from_hash(rpc, 'foo', '698fa7f')

    captured = capsys.readouterr()

    assert 'No patch has the hash provided' in captured.err
    assert captured.out == ''


def test_patch_id_from_hash__invalid_id(capsys):
    rpc = mock.Mock()
    rpc.patch_get_by_project_hash.return_value = {'id': 'xyz'}

    with pytest.raises(SystemExit):
        shell.patch_id_from_hash(rpc, 'foo', '698fa7f')

    captured = capsys.readouterr()

    assert 'Invalid patch ID obtained from server' in captured.err
    assert captured.out == ''


def test_patch_id_from_hash():
    rpc = mock.Mock()
    rpc.patch_get_by_project_hash.return_value = {'id': '1'}

    result = shell.patch_id_from_hash(rpc, 'foo', '698fa7f')

    assert result == 1
    rpc.patch_get_by_project_hash.assert_called_once_with('foo', '698fa7f')
    rpc.patch_get_by_hash.assert_not_called()


def test_patch_id_from_hash__legacy_function():
    rpc = mock.Mock()
    rpc.patch_get_by_project_hash.side_effect = xmlrpc.xmlrpclib.Fault(1, 'x')
    rpc.patch_get_by_hash.return_value = {'id': '1'}

    result = shell.patch_id_from_hash(rpc, 'foo', '698fa7f')

    assert result == 1
    rpc.patch_get_by_project_hash.assert_called_once_with('foo', '698fa7f')
    rpc.patch_get_by_hash.assert_called_once_with('698fa7f')


def test_list_patches(capsys):

    patches = fakes.fake_patches()

    shell.list_patches(patches)

    captured = capsys.readouterr()

    assert captured.out == """\
ID      State        Name
--      -----        ----
1157169 New          [1/3] Drop support for Python 3.4, add Python 3.7
1157170 Accepted     [2/3] docker: Simplify MySQL reset
1157168 Rejected     [3/3] docker: Use pyenv for Python versions
"""


def test_list_patches__format_option(capsys):

    patches = fakes.fake_patches()

    shell.list_patches(patches, '%{state}')

    captured = capsys.readouterr()

    assert captured.out == """\
New
Accepted
Rejected
"""


def test_list_patches__format_option_with_msgid(capsys):

    patches = fakes.fake_patches()

    shell.list_patches(patches, '%{_msgid_}')

    captured = capsys.readouterr()

    assert captured.out == """\
20190903170304.24325-1-stephen@that.guru
20190903170304.24325-2-stephen@that.guru
20190903170304.24325-3-stephen@that.guru
"""


@mock.patch.object(shell, 'list_patches')
def test_action_list__no_submitter_no_delegate(mock_list_patches, capsys):

    rpc = mock.Mock()
    filt = mock.Mock()

    shell.action_list(rpc, filt, None, None, None)

    filt.resolve_ids.assert_called_once_with(rpc)
    rpc.patch_list.assert_called_once_with(filt.d)
    mock_list_patches.assert_called_once_with(
        rpc.patch_list.return_value, None)


@mock.patch.object(shell, 'list_patches')
@mock.patch.object(shell, 'person_ids_by_name')
def test_action_list__submitter_filter(
        mock_person_lookup, mock_list_patches, capsys):

    fake_person = fakes.fake_people()[0]
    rpc = mock.Mock()
    filt = mock.Mock()

    mock_person_lookup.return_value = [fake_person['id']]
    rpc.person_get.return_value = fake_person

    shell.action_list(rpc, filt, 'Jeremy Kerr', None, None)

    captured = capsys.readouterr()

    assert 'Patches submitted by Jeremy Kerr <jk@ozlabs.org>:' in captured.out

    rpc.person_get.assert_called_once_with(fake_person['id'])
    rpc.patch_list.assert_called_once_with(filt.d)
    filt.add.assert_called_once_with('submitter_id', fake_person['id'])
    mock_person_lookup.assert_called_once_with(rpc, 'Jeremy Kerr')
    mock_list_patches.assert_called_once_with(
        rpc.patch_list.return_value, None)


@mock.patch.object(shell, 'list_patches')
@mock.patch.object(shell, 'person_ids_by_name')
def test_action_list__submitter_filter_no_matches(
        mock_person_lookup, mock_list_patches, capsys):

    rpc = mock.Mock()
    filt = mock.Mock()

    mock_person_lookup.return_value = []

    shell.action_list(rpc, filt, 'John Doe', None, None)

    captured = capsys.readouterr()

    assert captured.err == 'Note: Nobody found matching *John Doe*\n'

    rpc.person_get.assert_not_called()
    mock_person_lookup.assert_called_once_with(rpc, 'John Doe')
    mock_list_patches.assert_not_called()


@mock.patch.object(shell, 'list_patches')
@mock.patch.object(shell, 'person_ids_by_name')
def test_action_list__delegate_filter(
        mock_person_lookup, mock_list_patches, capsys):

    fake_person = fakes.fake_people()[0]
    rpc = mock.Mock()
    filt = mock.Mock()

    mock_person_lookup.return_value = [fake_person['id']]
    rpc.person_get.return_value = fake_person

    shell.action_list(rpc, filt, None, 'Jeremy Kerr', None)

    captured = capsys.readouterr()

    assert 'Patches delegated to Jeremy Kerr <jk@ozlabs.org>:' in captured.out

    rpc.person_get.assert_called_once_with(fake_person['id'])
    rpc.patch_list.assert_called_once_with(filt.d)
    filt.add.assert_called_once_with('delegate_id', fake_person['id'])
    mock_person_lookup.assert_called_once_with(rpc, 'Jeremy Kerr')
    mock_list_patches.assert_called_once_with(
        rpc.patch_list.return_value, None)


@mock.patch.object(shell, 'list_patches')
@mock.patch.object(shell, 'person_ids_by_name')
def test_action_list__delegate_filter_no_matches(
        mock_person_lookup, mock_list_patches, capsys):

    rpc = mock.Mock()
    filt = mock.Mock()

    mock_person_lookup.return_value = []

    shell.action_list(rpc, filt, None, 'John Doe', None)

    captured = capsys.readouterr()

    assert captured.err == 'Note: Nobody found matching *John Doe*\n'

    rpc.person_get.assert_not_called()
    mock_person_lookup.assert_called_once_with(rpc, 'John Doe')
    mock_list_patches.assert_not_called()


def test_action_check_list(capsys):
    rpc = mock.Mock()
    rpc.check_list.return_value = fakes.fake_checks()

    shell.action_check_list(rpc)

    captured = capsys.readouterr()

    assert captured.out == """\
ID    Context          State    Patch
--    -------          -----    -----
1     hello-world      success  1
"""


def test_action_check_info(capsys):
    fake_check = fakes.fake_checks()[0]

    rpc = mock.Mock()
    rpc.check_get.return_value = fake_check

    shell.action_check_info(rpc, 1)

    captured = capsys.readouterr()

    assert captured.out == """\
Information for check id 1
--------------------------
- context       : hello-world
- id            : 1
- patch         : 1
- state         : success
"""


def test_action_check_create():
    rpc = mock.Mock()

    args = (1, 'hello-world', 'success', 'https://example.com',
            'This is a sample check')

    shell.action_check_create(rpc, *args)

    rpc.check_create.assert_called_once_with(*args)


def test_action_check_create__error(capsys):
    rpc = mock.Mock()
    rpc.check_create.side_effect = xmlrpc.xmlrpclib.Fault(1, 'x')

    args = (1, 'hello-world', 'success', 'https://example.com',
            'This is a sample check')

    shell.action_check_create(rpc, *args)

    captured = capsys.readouterr()

    assert captured.err == 'Error creating check: x\n'


def test_action_states(capsys):
    rpc = mock.Mock()
    rpc.state_list.return_value = fakes.fake_states()

    shell.action_states(rpc)

    captured = capsys.readouterr()

    assert captured.out == """\
ID    Name
--    ----
1     New
"""


def test_action_info(capsys):
    rpc = mock.Mock()
    rpc.patch_get.return_value = fakes.fake_patches()[0]

    shell.action_info(rpc, 1157169)

    captured = capsys.readouterr()

    assert captured.out == """\
Information for patch id 1157169
--------------------------------
- filename      : 1-3--Drop-support-for-Python-3-4--add-Python-3-7
- id            : 1157169
- msgid         : <20190903170304.24325-1-stephen@that.guru>
- name          : [1/3] Drop support for Python 3.4, add Python 3.7
- state         : New
"""


def test_action_info__invalid_id(capsys):
    rpc = mock.Mock()
    rpc.patch_get.return_value = {}

    with pytest.raises(SystemExit):
        shell.action_info(rpc, 1)

    captured = capsys.readouterr()

    assert captured.out == ''
    assert captured.err == 'Error getting information on patch ID 1\n'


@mock.patch.object(shell.io, 'open')
@mock.patch.object(shell.os.path, 'basename')
@mock.patch.object(shell.os.path, 'exists')
def test_action_get(mock_exists, mock_basename, mock_open, capsys):
    fake_patch = fakes.fake_patches()[0]
    rpc = mock.Mock()
    rpc.patch_get.return_value = fake_patch
    rpc.patch_get_mbox.return_value = 'foo'
    mock_exists.side_effect = [True, False]
    mock_basename.return_value = fake_patch['filename']

    shell.action_get(rpc, 1157169)

    captured = capsys.readouterr()

    mock_basename.assert_called_once_with(
        '1-3--Drop-support-for-Python-3-4--add-Python-3-7')
    mock_exists.assert_has_calls([
        mock.call('1-3--Drop-support-for-Python-3-4--add-Python-3-7.patch'),
        mock.call('1-3--Drop-support-for-Python-3-4--add-Python-3-7.0.patch'),
    ])
    mock_open.assert_called_once_with(
        '1-3--Drop-support-for-Python-3-4--add-Python-3-7.0.patch', 'w',
        encoding='utf-8')

    assert captured.out == """\
Saved patch to 1-3--Drop-support-for-Python-3-4--add-Python-3-7.0.patch
"""


def test_action_get__invalid_id(capsys):
    rpc = mock.Mock()
    rpc.patch_get.return_value = {}
    rpc.patch_get_mbox.return_value = ''

    with pytest.raises(SystemExit):
        shell.action_get(rpc, 1)

    captured = capsys.readouterr()

    assert captured.out == ''
    assert captured.err == 'Unable to get patch 1\n'


@mock.patch.object(shell.subprocess, 'Popen')
def _test_action_apply(apply_cmd, mock_popen):
    rpc = mock.Mock()
    rpc.patch_get.return_value = fakes.fake_patches()[0]
    rpc.patch_get_mbox.return_value = 'foo'

    args = [rpc, 1157169]
    if apply_cmd:
        args.append(apply_cmd)

    result = shell.action_apply(*args)

    if not apply_cmd:
        apply_cmd = ['patch', '-p1']

    mock_popen.assert_called_once_with(
        apply_cmd, stdin=shell.subprocess.PIPE)
    mock_popen.return_value.communicate.assert_called_once_with(
        b'foo')
    assert result == mock_popen.return_value.returncode


def test_action_apply(capsys):
    _test_action_apply(None)

    captured = capsys.readouterr()

    assert captured.out == """\
Applying patch #1157169 to current directory
Description: [1/3] Drop support for Python 3.4, add Python 3.7
"""
    assert captured.err == ''


def test_action_apply__with_apply_cmd(capsys):
    _test_action_apply(['git-am', '-3'])

    captured = capsys.readouterr()

    assert captured.out == """\
Applying patch #1157169 using "git-am -3"
Description: [1/3] Drop support for Python 3.4, add Python 3.7
"""
    assert captured.err == ''


@mock.patch.object(shell.subprocess, 'Popen')
def test_action_apply__failed(mock_popen, capsys):
    rpc = mock.Mock()
    rpc.patch_get.return_value = fakes.fake_patches()[0]
    rpc.patch_get_mbox.return_value = ''

    with pytest.raises(SystemExit):
        shell.action_apply(rpc, 1)

    captured = capsys.readouterr()

    assert captured.out == """\
Applying patch #1 to current directory
Description: [1/3] Drop support for Python 3.4, add Python 3.7
"""
    assert captured.err == 'Error: No patch content found\n'

    mock_popen.assert_not_called()


def test_action_apply__invalid_id(capsys):
    rpc = mock.Mock()
    rpc.patch_get.return_value = {}

    with pytest.raises(SystemExit):
        shell.action_apply(rpc, 1)

    captured = capsys.readouterr()

    assert captured.out == ''
    assert captured.err == 'Error getting information on patch ID 1\n'


def test_action_update_patch__invalid_id(capsys):
    rpc = mock.Mock()
    rpc.patch_get.return_value = {}

    with pytest.raises(SystemExit):
        shell.action_update_patch(rpc, 1)

    captured = capsys.readouterr()

    assert captured.out == ''
    assert captured.err == 'Error getting information on patch ID 1\n'


@mock.patch.object(shell, 'state_id_by_name')
def test_action_update_patch(mock_get_state, capsys):
    rpc = mock.Mock()
    rpc.patch_get.return_value = fakes.fake_patches()[0]
    rpc.patch_set.return_value = True
    mock_get_state.return_value = 1

    shell.action_update_patch(rpc, 1157169, 'Accepted', 'yes', '698fa7f')

    rpc.patch_set.assert_called_once_with(
        1157169, {'state': 1, 'commit_ref': '698fa7f', 'archived': True})
    mock_get_state.assert_called_once_with(rpc, 'Accepted')


@mock.patch.object(shell, 'state_id_by_name')
def test_action_update_patch__invalid_state(mock_get_state, capsys):
    rpc = mock.Mock()
    rpc.patch_get.return_value = fakes.fake_patches()[0]
    rpc.patch_set.return_value = True
    mock_get_state.return_value = 0

    with pytest.raises(SystemExit):
        shell.action_update_patch(rpc, 1157169, state='Accccccepted')

    mock_get_state.assert_called_once_with(rpc, 'Accccccepted')

    captured = capsys.readouterr()

    assert captured.out == ''
    assert captured.err == 'Error: No State found matching Accccccepted*\n'


def test_action_update_patch__error(capsys):
    rpc = mock.Mock()
    rpc.patch_get.return_value = fakes.fake_patches()[0]
    rpc.patch_set.side_effect = xmlrpc.xmlrpclib.Fault(1, 'x')

    shell.action_update_patch(rpc, 1157169)

    rpc.patch_set.assert_called_once_with(1157169, {})

    captured = capsys.readouterr()

    assert captured.out == ''
    assert captured.err == """\
Error updating patch: x
Patch not updated
"""


def test_action_update_patch__no_updates(capsys):
    rpc = mock.Mock()
    rpc.patch_get.return_value = fakes.fake_patches()[0]
    rpc.patch_set.return_value = None

    shell.action_update_patch(rpc, 1157169)

    rpc.patch_set.assert_called_once_with(1157169, {})

    captured = capsys.readouterr()

    assert captured.out == ''
    assert captured.err == 'Patch not updated\n'
