import mock

from pwclient import utils

from .test_shell import FakeConfig


@mock.patch.object(utils.configparser, 'ConfigParser')
@mock.patch.object(utils.shutil, 'copy2', new=mock.Mock())
@mock.patch.object(utils, 'open', new_callable=mock.mock_open, read_data='1')
def test_migrate_config(mock_open, mock_config, capsys):

    old_config = FakeConfig({
        'base': {
            'project': 'foo',
            'url': 'https://example.com/',
        },
        'auth': {
            'username': 'user',
            'password': 'pass',
        },
    })
    new_config = FakeConfig()
    mock_config.return_value = new_config

    utils.migrate_old_config_file('foo', old_config)

    captured = capsys.readouterr()

    assert 'foo is in the old format. Migrating it...' in captured.err
    assert captured.out == ''
