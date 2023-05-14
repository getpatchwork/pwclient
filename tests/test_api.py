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
