from unittest import mock

import pytest

from pwclient import api
from pwclient import exceptions


def test_xmlrpc_init__missing_username():
    with pytest.raises(exceptions.ConfigError) as exc:
        api.XMLRPC('https://example.com/xmlrpc', username='user')

    assert 'You must provide both a username and a password ' in str(exc.value)


def test_xmlrpc_init__invalid_auth():
    """The XML-RPC API doesn't support tokens."""
    with pytest.raises(exceptions.ConfigError) as exc:
        api.XMLRPC('https://example.com/xmlrpc', token='foo')

    assert 'The XML-RPC API does not support API tokens' in str(exc.value)


def test_rest_init__strip_trailing_slash():
    """Ensure we strip the trailing slash."""
    client = api.REST('https://patchwork.kernel.org/api/')
    assert 'https://patchwork.kernel.org/api' == client._server


def test_rest_init__transform_legacy_url(capsys):
    """Ensure we handle legacy XML-RPC URLs."""
    client = api.REST('https://patchwork.kernel.org/xmlrpc/')
    assert 'https://patchwork.kernel.org/api' == client._server

    captured = capsys.readouterr()

    assert (
        'Automatically converted XML-RPC URL to REST API URL.' in captured.err
    )


def test_rest_client__create():
    """Validate the _create helper."""
    client = api.REST(
        'https://patchwork.kernel.org/api',
        username='user',
        password='pass',
    )

    fake_response = mock.MagicMock()
    fake_response.read.return_value = (
        b'{"id": 1, "state": "success", "context": "foo"}'
    )
    fake_response.getheaders.return_value = []

    with mock.patch('urllib.request.urlopen') as mock_open:
        fake_response.__enter__.return_value = fake_response
        mock_open.return_value = fake_response

        expected = {'id': 1, 'state': 'success', 'context': 'foo'}
        actual = client._create(
            'patches',
            resource_id=1,
            subresource_type='checks',
            data={'context': 'foo', 'state': 'success'},
        )

        assert expected == actual


def test_rest_client__update():
    """Validate the _update helper."""
    client = api.REST(
        'https://patchwork.kernel.org/api',
        username='user',
        password='pass',
    )

    fake_response = mock.MagicMock()
    fake_response.read.return_value = b'{"id": 1, "archived": true}'
    fake_response.getheaders.return_value = []

    with mock.patch('urllib.request.urlopen') as mock_open:
        fake_response.__enter__.return_value = fake_response
        mock_open.return_value = fake_response

        expected = {'id': 1, 'archived': True}
        actual = client._update(
            'patches',
            1,
            {'archived': True},
        )

        assert expected == actual


def test_rest_client__detail():
    """Validate the _detail helper."""
    client = api.REST(
        'https://patchwork.kernel.org/api',
        username='user',
        password='pass',
    )

    fake_response = mock.MagicMock()
    fake_response.read.return_value = b'{"id": 1, "name": "foo"}'
    fake_response.getheaders.return_value = []

    with mock.patch('urllib.request.urlopen') as mock_open:
        fake_response.__enter__.return_value = fake_response
        mock_open.return_value = fake_response

        expected = {'id': 1, 'name': 'foo'}
        actual = client._detail(
            'patches',
            1,
        )

        assert expected == actual


def test_rest_client__list():
    """Validate the _list helper."""
    client = api.REST(
        'https://patchwork.kernel.org/api',
        username='user',
        password='pass',
    )

    fake_response = mock.MagicMock()
    fake_response.read.side_effect = [
        b'[{"id": 1}]',
        b'[{"id": 2}]',
    ]
    fake_response.getheaders.side_effect = [
        [
            (
                'Link',
                '<https://patchwork.kernel.org/api/patches/?page=2&project=patchwork>; rel="next"',
            )
        ],
        [],
    ]

    with mock.patch('urllib.request.urlopen') as mock_open:
        fake_response.__enter__.return_value = fake_response
        mock_open.return_value = fake_response

        expected = [{'id': 1}, {'id': 2}]
        actual = list(client._list('patches'))

        assert expected == actual
