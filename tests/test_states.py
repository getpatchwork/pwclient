import mock

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


def test_state_id_by_name__empty_name():
    rpc = mock.Mock()

    result = states.state_id_by_name(rpc, '')

    assert result == 0
    rpc.state_list.assert_not_called()


def test_state_id_by_name__no_matches():
    rpc = mock.Mock()
    rpc.state_list.return_value = [
        {'id': 1, 'name': 'bar'},
        {'id': 2, 'name': 'baz'},
    ]

    result = states.state_id_by_name(rpc, 'foo')

    assert result == 0
    rpc.state_list.assert_called_once_with('foo', 0)


def test_state_id_by_name():
    rpc = mock.Mock()
    rpc.state_list.return_value = [
        {'id': 1, 'name': 'bar'},
        {'id': 2, 'name': 'baz'},
        {'id': 3, 'name': 'foo'},
    ]

    result = states.state_id_by_name(rpc, 'foo')

    assert result == 3
    rpc.state_list.assert_called_once_with('foo', 0)
