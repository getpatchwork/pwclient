from unittest import mock

from pwclient import states

from . import fakes


def test_action_list(capsys):
    rpc = mock.Mock()
    rpc.state_list.return_value = fakes.fake_states()

    states.action_list(rpc)

    captured = capsys.readouterr()

    assert captured.out == """\
ID    Name
--    ----
1     New
"""
