import mock

from pwclient import checks
from pwclient import xmlrpc

from . import fakes


def test_action_check_list(capsys):
    rpc = mock.Mock()
    rpc.check_list.return_value = fakes.fake_checks()

    checks.action_list(rpc)

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

    checks.action_info(rpc, 1)

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

    checks.action_create(rpc, *args)

    rpc.check_create.assert_called_once_with(*args)


def test_action_check_create__error(capsys):
    rpc = mock.Mock()
    rpc.check_create.side_effect = xmlrpc.xmlrpclib.Fault(1, 'x')

    args = (1, 'hello-world', 'success', 'https://example.com',
            'This is a sample check')

    checks.action_create(rpc, *args)

    captured = capsys.readouterr()

    assert captured.err == 'Error creating check: x\n'
