import mock

from pwclient import people


def test_person_ids_by_name():
    rpc = mock.Mock()
    rpc.person_list.return_value = [
        {'id': 3, 'name': 'foo'},
        {'id': 35, 'name': 'foobar'},
    ]

    result = people.person_ids_by_name(rpc, 'foo')

    assert result == [3, 35]
    rpc.person_list.assert_called_once_with('foo', 0)


def test_person_ids_by_name__empty_name():
    rpc = mock.Mock()

    result = people.person_ids_by_name(rpc, '')

    assert result == []
    rpc.person_list.assert_not_called()


def test_person_ids_by_name__no_matches():
    rpc = mock.Mock()
    rpc.person_list.return_value = []

    result = people.person_ids_by_name(rpc, 'foo')

    assert result == []
    rpc.person_list.assert_called_once_with('foo', 0)
