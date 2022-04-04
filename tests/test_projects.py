from unittest import mock

from pwclient import projects

from . import fakes


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
