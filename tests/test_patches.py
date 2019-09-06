import mock
import pytest

from pwclient import patches
from pwclient import people
from pwclient import states
from pwclient import xmlrpc

from . import fakes


def test_patch_id_from_hash__no_matches(capsys):
    rpc = mock.Mock()
    rpc.patch_get_by_project_hash.return_value = {}

    with pytest.raises(SystemExit):
        patches.patch_id_from_hash(rpc, 'foo', '698fa7f')

    captured = capsys.readouterr()

    assert 'No patch has the hash provided' in captured.err
    assert captured.out == ''


def test_patch_id_from_hash__invalid_id(capsys):
    rpc = mock.Mock()
    rpc.patch_get_by_project_hash.return_value = {'id': 'xyz'}

    with pytest.raises(SystemExit):
        patches.patch_id_from_hash(rpc, 'foo', '698fa7f')

    captured = capsys.readouterr()

    assert 'Invalid patch ID obtained from server' in captured.err
    assert captured.out == ''


def test_patch_id_from_hash():
    rpc = mock.Mock()
    rpc.patch_get_by_project_hash.return_value = {'id': '1'}

    result = patches.patch_id_from_hash(rpc, 'foo', '698fa7f')

    assert result == 1
    rpc.patch_get_by_project_hash.assert_called_once_with('foo', '698fa7f')
    rpc.patch_get_by_hash.assert_not_called()


def test_patch_id_from_hash__legacy_function():
    rpc = mock.Mock()
    rpc.patch_get_by_project_hash.side_effect = xmlrpc.xmlrpclib.Fault(1, 'x')
    rpc.patch_get_by_hash.return_value = {'id': '1'}

    result = patches.patch_id_from_hash(rpc, 'foo', '698fa7f')

    assert result == 1
    rpc.patch_get_by_project_hash.assert_called_once_with('foo', '698fa7f')
    rpc.patch_get_by_hash.assert_called_once_with('698fa7f')


def test_list_patches(capsys):

    fake_patches = fakes.fake_patches()

    patches._list_patches(fake_patches)

    captured = capsys.readouterr()

    assert captured.out == """\
ID      State        Name
--      -----        ----
1157169 New          [1/3] Drop support for Python 3.4, add Python 3.7
1157170 Accepted     [2/3] docker: Simplify MySQL reset
1157168 Rejected     [3/3] docker: Use pyenv for Python versions
"""


def test_list_patches__format_option(capsys):

    fake_patches = fakes.fake_patches()

    patches._list_patches(fake_patches, '%{state}')

    captured = capsys.readouterr()

    assert captured.out == """\
New
Accepted
Rejected
"""


def test_list_patches__format_option_with_msgid(capsys):

    fake_patches = fakes.fake_patches()

    patches._list_patches(fake_patches, '%{_msgid_}')

    captured = capsys.readouterr()

    assert captured.out == """\
20190903170304.24325-1-stephen@that.guru
20190903170304.24325-2-stephen@that.guru
20190903170304.24325-3-stephen@that.guru
"""


@mock.patch.object(patches, '_list_patches')
def test_action_list__no_submitter_no_delegate(mock_list_patches, capsys):

    rpc = mock.Mock()
    filt = mock.Mock()

    patches.action_list(rpc, filt, None, None, None)

    filt.resolve_ids.assert_called_once_with(rpc)
    rpc.patch_list.assert_called_once_with(filt.d)
    mock_list_patches.assert_called_once_with(
        rpc.patch_list.return_value, None)


@mock.patch.object(patches, '_list_patches')
@mock.patch.object(people, 'person_ids_by_name')
def test_action_list__submitter_filter(
        mock_person_lookup, mock_list_patches, capsys):

    fake_person = fakes.fake_people()[0]
    rpc = mock.Mock()
    filt = mock.Mock()

    mock_person_lookup.return_value = [fake_person['id']]
    rpc.person_get.return_value = fake_person

    patches.action_list(rpc, filt, 'Jeremy Kerr', None, None)

    captured = capsys.readouterr()

    assert 'Patches submitted by Jeremy Kerr <jk@ozlabs.org>:' in captured.out

    rpc.person_get.assert_called_once_with(fake_person['id'])
    rpc.patch_list.assert_called_once_with(filt.d)
    filt.add.assert_called_once_with('submitter_id', fake_person['id'])
    mock_person_lookup.assert_called_once_with(rpc, 'Jeremy Kerr')
    mock_list_patches.assert_called_once_with(
        rpc.patch_list.return_value, None)


@mock.patch.object(patches, '_list_patches')
@mock.patch.object(people, 'person_ids_by_name')
def test_action_list__submitter_filter_no_matches(
        mock_person_lookup, mock_list_patches, capsys):

    rpc = mock.Mock()
    filt = mock.Mock()

    mock_person_lookup.return_value = []

    patches.action_list(rpc, filt, 'John Doe', None, None)

    captured = capsys.readouterr()

    assert captured.err == 'Note: Nobody found matching *John Doe*\n'

    rpc.person_get.assert_not_called()
    mock_person_lookup.assert_called_once_with(rpc, 'John Doe')
    mock_list_patches.assert_not_called()


@mock.patch.object(patches, '_list_patches')
@mock.patch.object(people, 'person_ids_by_name')
def test_action_list__delegate_filter(
        mock_person_lookup, mock_list_patches, capsys):

    fake_person = fakes.fake_people()[0]
    rpc = mock.Mock()
    filt = mock.Mock()

    mock_person_lookup.return_value = [fake_person['id']]
    rpc.person_get.return_value = fake_person

    patches.action_list(rpc, filt, None, 'Jeremy Kerr', None)

    captured = capsys.readouterr()

    assert 'Patches delegated to Jeremy Kerr <jk@ozlabs.org>:' in captured.out

    rpc.person_get.assert_called_once_with(fake_person['id'])
    rpc.patch_list.assert_called_once_with(filt.d)
    filt.add.assert_called_once_with('delegate_id', fake_person['id'])
    mock_person_lookup.assert_called_once_with(rpc, 'Jeremy Kerr')
    mock_list_patches.assert_called_once_with(
        rpc.patch_list.return_value, None)


@mock.patch.object(patches, '_list_patches')
@mock.patch.object(people, 'person_ids_by_name')
def test_action_list__delegate_filter_no_matches(
        mock_person_lookup, mock_list_patches, capsys):

    rpc = mock.Mock()
    filt = mock.Mock()

    mock_person_lookup.return_value = []

    patches.action_list(rpc, filt, None, 'John Doe', None)

    captured = capsys.readouterr()

    assert captured.err == 'Note: Nobody found matching *John Doe*\n'

    rpc.person_get.assert_not_called()
    mock_person_lookup.assert_called_once_with(rpc, 'John Doe')
    mock_list_patches.assert_not_called()


def test_action_info(capsys):
    rpc = mock.Mock()
    rpc.patch_get.return_value = fakes.fake_patches()[0]

    patches.action_info(rpc, 1157169)

    captured = capsys.readouterr()

    assert captured.out == """\
Information for patch id 1157169
--------------------------------
- filename      : 1-3--Drop-support-for-Python-3-4--add-Python-3-7
- id            : 1157169
- msgid         : <20190903170304.24325-1-stephen@that.guru>
- name          : [1/3] Drop support for Python 3.4, add Python 3.7
- state         : New
"""


def test_action_info__invalid_id(capsys):
    rpc = mock.Mock()
    rpc.patch_get.return_value = {}

    with pytest.raises(SystemExit):
        patches.action_info(rpc, 1)

    captured = capsys.readouterr()

    assert captured.out == ''
    assert captured.err == 'Error getting information on patch ID 1\n'


@mock.patch.object(patches.io, 'open')
@mock.patch.object(patches.os.path, 'basename')
@mock.patch.object(patches.os.path, 'exists')
def test_action_get(mock_exists, mock_basename, mock_open, capsys):
    fake_patch = fakes.fake_patches()[0]
    rpc = mock.Mock()
    rpc.patch_get.return_value = fake_patch
    rpc.patch_get_mbox.return_value = 'foo'
    mock_exists.side_effect = [True, False]
    mock_basename.return_value = fake_patch['filename']

    patches.action_get(rpc, 1157169)

    captured = capsys.readouterr()

    mock_basename.assert_called_once_with(
        '1-3--Drop-support-for-Python-3-4--add-Python-3-7')
    mock_exists.assert_has_calls([
        mock.call('1-3--Drop-support-for-Python-3-4--add-Python-3-7.patch'),
        mock.call('1-3--Drop-support-for-Python-3-4--add-Python-3-7.0.patch'),
    ])
    mock_open.assert_called_once_with(
        '1-3--Drop-support-for-Python-3-4--add-Python-3-7.0.patch', 'w',
        encoding='utf-8')

    assert captured.out == """\
Saved patch to 1-3--Drop-support-for-Python-3-4--add-Python-3-7.0.patch
"""


def test_action_get__invalid_id(capsys):
    rpc = mock.Mock()
    rpc.patch_get.return_value = {}
    rpc.patch_get_mbox.return_value = ''

    with pytest.raises(SystemExit):
        patches.action_get(rpc, 1)

    captured = capsys.readouterr()

    assert captured.out == ''
    assert captured.err == 'Unable to get patch 1\n'


@mock.patch.object(patches.os.environ, 'get')
@mock.patch.object(patches.subprocess, 'Popen')
def test_action_view__no_pager(mock_popen, mock_env, capsys):
    rpc = mock.Mock()
    rpc.patch_get_mbox.return_value = 'foo'
    mock_env.return_value = None

    patches.action_view(rpc, [1])

    mock_popen.assert_not_called()
    rpc.patch_get_mbox.assert_called_once_with(1)

    captured = capsys.readouterr()

    assert captured.out == 'foo\n'


@mock.patch.object(patches.os.environ, 'get')
@mock.patch.object(patches.subprocess, 'Popen')
def test_action_view__no_pager_multiple_patches(mock_popen, mock_env, capsys):
    rpc = mock.Mock()
    rpc.patch_get_mbox.side_effect = ['foo', 'bar', 'baz']
    mock_env.return_value = None

    patches.action_view(rpc, [1, 2, 3])

    captured = capsys.readouterr()

    mock_popen.assert_not_called()
    assert captured.out == 'foo\nbar\nbaz\n'


@mock.patch.object(patches.os.environ, 'get')
@mock.patch.object(patches.subprocess, 'Popen')
def test_view__with_pager(mock_popen, mock_env, capsys):
    rpc = mock.Mock()
    rpc.patch_get_mbox.return_value = 'foo'
    mock_env.return_value = 'less'

    patches.action_view(rpc, [1])

    mock_popen.assert_called_once_with(['less'], stdin=mock.ANY)
    mock_popen.return_value.communicate.assert_has_calls([
        mock.call(input=b'foo'),
    ])

    captured = capsys.readouterr()
    assert captured.out == ''


@mock.patch.object(patches.os.environ, 'get')
@mock.patch.object(patches.subprocess, 'Popen')
def test_view__with_pager_multiple_ids(mock_popen, mock_env, capsys):
    rpc = mock.Mock()
    rpc.patch_get_mbox.side_effect = ['foo', 'bar', 'baz']
    mock_env.return_value = 'less'

    patches.action_view(rpc, [1, 2, 3])

    mock_popen.assert_called_once_with(['less'], stdin=mock.ANY)
    mock_popen.return_value.communicate.assert_has_calls([
        mock.call(input=b'foo\nbar\nbaz'),
    ])

    captured = capsys.readouterr()
    assert captured.out == ''


@mock.patch.object(patches.subprocess, 'Popen')
def _test_action_apply(apply_cmd, mock_popen):
    rpc = mock.Mock()
    rpc.patch_get.return_value = fakes.fake_patches()[0]
    rpc.patch_get_mbox.return_value = 'foo'

    args = [rpc, 1157169]
    if apply_cmd:
        args.append(apply_cmd)

    result = patches.action_apply(*args)

    if not apply_cmd:
        apply_cmd = ['patch', '-p1']

    mock_popen.assert_called_once_with(
        apply_cmd, stdin=patches.subprocess.PIPE)
    mock_popen.return_value.communicate.assert_called_once_with(
        b'foo')
    assert result == mock_popen.return_value.returncode


def test_action_apply(capsys):
    _test_action_apply(None)

    captured = capsys.readouterr()

    assert captured.out == """\
Applying patch #1157169 to current directory
Description: [1/3] Drop support for Python 3.4, add Python 3.7
"""
    assert captured.err == ''


def test_action_apply__with_apply_cmd(capsys):
    _test_action_apply(['git-am', '-3'])

    captured = capsys.readouterr()

    assert captured.out == """\
Applying patch #1157169 using "git-am -3"
Description: [1/3] Drop support for Python 3.4, add Python 3.7
"""
    assert captured.err == ''


@mock.patch.object(patches.subprocess, 'Popen')
def test_action_apply__failed(mock_popen, capsys):
    rpc = mock.Mock()
    rpc.patch_get.return_value = fakes.fake_patches()[0]
    rpc.patch_get_mbox.return_value = ''

    with pytest.raises(SystemExit):
        patches.action_apply(rpc, 1)

    captured = capsys.readouterr()

    assert captured.out == """\
Applying patch #1 to current directory
Description: [1/3] Drop support for Python 3.4, add Python 3.7
"""
    assert captured.err == 'Error: No patch content found\n'

    mock_popen.assert_not_called()


def test_action_apply__invalid_id(capsys):
    rpc = mock.Mock()
    rpc.patch_get.return_value = {}

    with pytest.raises(SystemExit):
        patches.action_apply(rpc, 1)

    captured = capsys.readouterr()

    assert captured.out == ''
    assert captured.err == 'Error getting information on patch ID 1\n'


def test_action_update__invalid_id(capsys):
    rpc = mock.Mock()
    rpc.patch_get.return_value = {}

    with pytest.raises(SystemExit):
        patches.action_update(rpc, 1)

    captured = capsys.readouterr()

    assert captured.out == ''
    assert captured.err == 'Error getting information on patch ID 1\n'


@mock.patch.object(states, 'state_id_by_name')
def test_action_update(mock_get_state, capsys):
    rpc = mock.Mock()
    rpc.patch_get.return_value = fakes.fake_patches()[0]
    rpc.patch_set.return_value = True
    mock_get_state.return_value = 1

    patches.action_update(rpc, 1157169, 'Accepted', 'yes', '698fa7f')

    rpc.patch_set.assert_called_once_with(
        1157169, {'state': 1, 'commit_ref': '698fa7f', 'archived': True})
    mock_get_state.assert_called_once_with(rpc, 'Accepted')


@mock.patch.object(states, 'state_id_by_name')
def test_action_update__invalid_state(mock_get_state, capsys):
    rpc = mock.Mock()
    rpc.patch_get.return_value = fakes.fake_patches()[0]
    rpc.patch_set.return_value = True
    mock_get_state.return_value = 0

    with pytest.raises(SystemExit):
        patches.action_update(rpc, 1157169, state='Accccccepted')

    mock_get_state.assert_called_once_with(rpc, 'Accccccepted')

    captured = capsys.readouterr()

    assert captured.out == ''
    assert captured.err == 'Error: No State found matching Accccccepted*\n'


def test_action_update__error(capsys):
    rpc = mock.Mock()
    rpc.patch_get.return_value = fakes.fake_patches()[0]
    rpc.patch_set.side_effect = xmlrpc.xmlrpclib.Fault(1, 'x')

    patches.action_update(rpc, 1157169)

    rpc.patch_set.assert_called_once_with(1157169, {})

    captured = capsys.readouterr()

    assert captured.out == ''
    assert captured.err == """\
Error updating patch: x
Patch not updated
"""


def test_action_update__no_updates(capsys):
    rpc = mock.Mock()
    rpc.patch_get.return_value = fakes.fake_patches()[0]
    rpc.patch_set.return_value = None

    patches.action_update(rpc, 1157169)

    rpc.patch_set.assert_called_once_with(1157169, {})

    captured = capsys.readouterr()

    assert captured.out == ''
    assert captured.err == 'Patch not updated\n'
