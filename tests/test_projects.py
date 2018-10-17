import mock

from pwclient import projects

from . import fakes


def test_project_id_by_name__empty_linkname():
    rpc = mock.Mock()

    result = projects.project_id_by_name(rpc, '')

    assert result == 0
    rpc.project_list.assert_not_called()


def test_project_id_by_name__no_matches():
    rpc = mock.Mock()
    rpc.project_list.return_value = [
        {'id': 1, 'linkname': 'bar'},
        {'id': 2, 'linkname': 'baz'},
    ]

    result = projects.project_id_by_name(rpc, 'foo')

    assert result == 0
    rpc.project_list.assert_called_once_with('foo', 0)


def test_project_id_by_name():
    rpc = mock.Mock()
    rpc.project_list.return_value = [
        {'id': 1, 'linkname': 'bar'},
        {'id': 2, 'linkname': 'baz'},
        {'id': 3, 'linkname': 'foo'},
    ]

    result = projects.project_id_by_name(rpc, 'foo')

    assert result == 3
    rpc.project_list.assert_called_once_with('foo', 0)


def test_action_list(capsys):
    rpc = mock.Mock()
    rpc.project_list.return_value = fakes.fake_projects()

    projects.action_list(rpc)

    captured = capsys.readouterr()

    assert captured.out == """\
ID    Name                     Description
--    ----                     -----------
1     patchwork                Patchwork
"""
