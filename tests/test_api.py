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
