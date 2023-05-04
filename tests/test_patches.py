from unittest import mock

import pytest

from pwclient import exceptions
from pwclient import patches

from . import fakes

FAKE_PROJECT = 'defaultproject'
FAKE_PROJECT_ID = 42


def test_patch_id_from_hash__no_matches(capsys):
    api = mock.Mock()
    api.patch_get_by_project_hash.return_value = {}

    with pytest.raises(SystemExit):
        patches.patch_id_from_hash(api, 'foo', '698fa7f')

    captured = capsys.readouterr()

    assert 'No patch has the hash provided' in captured.err
    assert captured.out == ''


def test_patch_id_from_hash__invalid_id(capsys):
    api = mock.Mock()
    api.patch_get_by_project_hash.return_value = {'id': 'xyz'}

    with pytest.raises(SystemExit):
        patches.patch_id_from_hash(api, 'foo', '698fa7f')

    captured = capsys.readouterr()

    assert 'Invalid patch ID obtained from server' in captured.err
    assert captured.out == ''


def test_patch_id_from_hash():
    api = mock.Mock()
    api.patch_get_by_project_hash.return_value = {'id': '1'}

    result = patches.patch_id_from_hash(api, 'foo', '698fa7f')

    assert result == 1
    api.patch_get_by_project_hash.assert_called_once_with('foo', '698fa7f')
    api.patch_get_by_hash.assert_not_called()


def test_list_patches(capsys):

    fake_patches = fakes.fake_patches()

    patches._list_patches(fake_patches)

    captured = capsys.readouterr()

    assert (
        captured.out
        == """\
ID      State        Name
--      -----        ----
1157169 New          [1/3] Drop support for Python 3.4, add Python 3.7
1157170 Accepted     [2/3] docker: Simplify MySQL reset
1157168 Rejected     [3/3] docker: Use pyenv for Python versions
"""
    )


def test_list_patches__format_option(capsys):

    fake_patches = fakes.fake_patches()

    patches._list_patches(fake_patches, '%{state}')

    captured = capsys.readouterr()

    assert (
        captured.out
        == """\
New
Accepted
Rejected
"""
    )


def test_list_patches__format_option_with_msgid(capsys):

    fake_patches = fakes.fake_patches()

    patches._list_patches(fake_patches, '%{_msgid_}')

    captured = capsys.readouterr()

    assert (
        captured.out
        == """\
20190903170304.24325-1-stephen@that.guru
20190903170304.24325-2-stephen@that.guru
20190903170304.24325-3-stephen@that.guru
"""
    )


@mock.patch.object(patches, '_list_patches')
def test_action_list__no_submitter_no_delegate(mock_list_patches, capsys):

    api = mock.Mock()

    patches.action_list(api, FAKE_PROJECT)

    api.patch_list.assert_called_once_with(
        project='defaultproject',
        submitter=None,
        delegate=None,
        state=None,
        archived=None,
        msgid=None,
        name=None,
        hash=None,
        max_count=None,
    )
    mock_list_patches.assert_called_once_with(
        api.patch_list.return_value,
        None,
    )


@mock.patch.object(patches, '_list_patches')
def test_action_list__submitter_filter(mock_list_patches, capsys):

    api = mock.Mock()
    api.patch_list.return_value = fakes.fake_patches()

    patches.action_list(api, FAKE_PROJECT, submitter='Joe Bloggs')

    captured = capsys.readouterr()

    assert (
        'Patches submitted by Joe Bloggs <joe.bloggs@example.com>:'
        in captured.out
    )  # noqa: E501

    api.patch_list.assert_called_once_with(
        project='defaultproject',
        submitter='Joe Bloggs',
        delegate=None,
        state=None,
        archived=None,
        msgid=None,
        name=None,
        hash=None,
        max_count=None,
    )
    mock_list_patches.assert_called_once_with(
        api.patch_list.return_value,
        None,
    )


@mock.patch.object(patches, '_list_patches')
def test_action_list__delegate_filter(mock_list_patches, capsys):

    api = mock.Mock()
    api.patch_list.return_value = fakes.fake_patches()

    patches.action_list(api, FAKE_PROJECT, delegate='admin')

    captured = capsys.readouterr()

    assert 'Patches delegated to admin:' in captured.out

    api.patch_list.assert_called_once_with(
        project='defaultproject',
        submitter=None,
        delegate='admin',
        state=None,
        archived=None,
        msgid=None,
        name=None,
        hash=None,
        max_count=None,
    )
    mock_list_patches.assert_called_once_with(
        api.patch_list.return_value,
        None,
    )


def test_action_info(capsys):
    api = mock.Mock()
    api.patch_get.return_value = fakes.fake_patches()[0]

    patches.action_info(api, 1157169)

    captured = capsys.readouterr()

    assert (
        captured.out
        == """\
Information for patch id 1157169
--------------------------------
- archived      : False
- commit_ref    :
- date          : 2000-12-31 00:11:22
- delegate      : admin
- delegate_id   : 1
- filename      : 1-3--Drop-support-for-Python-3-4--add-Python-3-7
- hash          :
- id            : 1157169
- msgid         : <20190903170304.24325-1-stephen@that.guru>
- name          : [1/3] Drop support for Python 3.4, add Python 3.7
- project       : my-project
- project_id    : 1
- state         : New
- state_id      : 1
- submitter     : Joe Bloggs <joe.bloggs@example.com>
- submitter_id  : 1
"""
    )


def test_action_info__invalid_id(capsys):
    api = mock.Mock()
    api.patch_get.side_effect = exceptions.APIError('foo')

    with pytest.raises(SystemExit):
        patches.action_info(api, 1)

    captured = capsys.readouterr()

    assert captured.out == ''
    assert captured.err == 'foo\n'


@mock.patch.object(patches.io, 'open')
@mock.patch.object(patches.os.path, 'basename')
@mock.patch.object(patches.os.path, 'exists')
def test_action_get(mock_exists, mock_basename, mock_open, capsys):
    api = mock.Mock()
    api.patch_get_mbox.return_value = (
        'foo',
        '1-3--Drop-support-for-Python-3-4--add-Python-3-7',
    )
    mock_exists.side_effect = [True, False]
    mock_basename.return_value = api.patch_get_mbox.return_value[1]

    patches.action_get(api, 1157169)

    captured = capsys.readouterr()

    mock_basename.assert_called_once_with(
        '1-3--Drop-support-for-Python-3-4--add-Python-3-7'
    )
    mock_exists.assert_has_calls(
        [
            mock.call(
                '1-3--Drop-support-for-Python-3-4--add-Python-3-7.patch'
            ),
            mock.call(
                '1-3--Drop-support-for-Python-3-4--add-Python-3-7.0.patch'
            ),
        ]
    )
    mock_open.assert_called_once_with(
        '1-3--Drop-support-for-Python-3-4--add-Python-3-7.0.patch',
        'x',
        encoding='utf-8',
    )

    assert (
        captured.out
        == """\
Saved patch to 1-3--Drop-support-for-Python-3-4--add-Python-3-7.0.patch
"""
    )


def test_action_get__invalid_id(capsys):
    api = mock.Mock()
    api.patch_get_mbox.side_effect = exceptions.APIError('foo')

    with pytest.raises(SystemExit):
        patches.action_get(api, 1)

    captured = capsys.readouterr()

    assert captured.out == ''
    assert captured.err == 'foo\n'


@mock.patch.object(patches.os.environ, 'get')
@mock.patch.object(patches.subprocess, 'Popen')
def test_action_view__no_pager(mock_popen, mock_env, capsys):
    api = mock.Mock()
    api.patch_get_mbox.return_value = (
        'foo',
        '1-3--Drop-support-for-Python-3-4--add-Python-3-7',
    )
    mock_env.return_value = None

    patches.action_view(api, [1])

    mock_popen.assert_not_called()
    api.patch_get_mbox.assert_called_once_with(1)

    captured = capsys.readouterr()

    assert captured.out == 'foo\n'


@mock.patch.object(patches.os.environ, 'get')
@mock.patch.object(patches.subprocess, 'Popen')
def test_action_view__no_pager_multiple_patches(mock_popen, mock_env, capsys):
    api = mock.Mock()
    api.patch_get_mbox.side_effect = [
        (
            'foo',
            '1-3--Drop-support-for-Python-3-4--add-Python-3-7',
        ),
        (
            'bar',
            '2-3-docker-Simplify-MySQL-reset',
        ),
        (
            'baz',
            '3-3-docker-Use-pyenv-for-Python-versions',
        ),
    ]
    mock_env.return_value = None

    patches.action_view(api, [1, 2, 3])

    captured = capsys.readouterr()

    mock_popen.assert_not_called()
    assert captured.out == 'foo\nbar\nbaz\n'


@mock.patch.object(patches.os.environ, 'get')
@mock.patch.object(patches.subprocess, 'Popen')
def test_view__with_pager(mock_popen, mock_env, capsys):
    api = mock.Mock()
    api.patch_get_mbox.return_value = (
        'foo',
        '1-3--Drop-support-for-Python-3-4--add-Python-3-7',
    )
    mock_env.return_value = 'less'

    patches.action_view(api, [1])

    mock_popen.assert_called_once_with(['less'], stdin=mock.ANY)
    mock_popen.return_value.communicate.assert_has_calls(
        [
            mock.call(input=b'foo'),
        ]
    )

    captured = capsys.readouterr()
    assert captured.out == ''


@mock.patch.object(patches.os.environ, 'get')
@mock.patch.object(patches.subprocess, 'Popen')
def test_view__with_pager_multiple_ids(mock_popen, mock_env, capsys):
    api = mock.Mock()
    api.patch_get_mbox.side_effect = [
        (
            'foo',
            '1-3--Drop-support-for-Python-3-4--add-Python-3-7',
        ),
        (
            'bar',
            '2-3-docker-Simplify-MySQL-reset',
        ),
        (
            'baz',
            '3-3-docker-Use-pyenv-for-Python-versions',
        ),
    ]
    mock_env.return_value = 'less'

    patches.action_view(api, [1, 2, 3])

    mock_popen.assert_called_once_with(['less'], stdin=mock.ANY)
    mock_popen.return_value.communicate.assert_has_calls(
        [
            mock.call(input=b'foo\nbar\nbaz'),
        ]
    )

    captured = capsys.readouterr()
    assert captured.out == ''


@mock.patch.object(patches.subprocess, 'Popen')
def _test_action_apply(apply_cmd, mock_popen):
    api = mock.Mock()
    api.patch_get.return_value = fakes.fake_patches()[0]
    api.patch_get_mbox.return_value = (
        'foo',
        '1-3--Drop-support-for-Python-3-4--add-Python-3-7',
    )

    args = [api, 1157169]
    if apply_cmd:
        args.append(apply_cmd)

    result = patches.action_apply(*args)

    if not apply_cmd:
        apply_cmd = ['patch', '-p1']

    mock_popen.assert_called_once_with(
        apply_cmd, stdin=patches.subprocess.PIPE
    )
    mock_popen.return_value.communicate.assert_called_once_with(b'foo')
    assert result == mock_popen.return_value.returncode


def test_action_apply(capsys):
    _test_action_apply(None)

    captured = capsys.readouterr()

    assert (
        captured.out
        == """\
Applying patch #1157169 to current directory
Description: [1/3] Drop support for Python 3.4, add Python 3.7
"""
    )
    assert captured.err == ''


def test_action_apply__with_apply_cmd(capsys):
    _test_action_apply(['git-am', '-3'])

    captured = capsys.readouterr()

    assert (
        captured.out
        == """\
Applying patch #1157169 using "git-am -3"
Description: [1/3] Drop support for Python 3.4, add Python 3.7
"""
    )
    assert captured.err == ''


@mock.patch.object(patches.subprocess, 'Popen')
def test_action_apply__failed(mock_popen, capsys):
    api = mock.Mock()
    api.patch_get.return_value = fakes.fake_patches()[0]
    api.patch_get_mbox.side_effect = exceptions.APIError('foo')

    with pytest.raises(SystemExit):
        patches.action_apply(api, 1)

    captured = capsys.readouterr()

    assert (
        captured.out
        == """\
Applying patch #1 to current directory
Description: [1/3] Drop support for Python 3.4, add Python 3.7
"""
    )
    assert captured.err == 'foo\n'

    mock_popen.assert_not_called()


def test_action_apply__invalid_id(capsys):
    api = mock.Mock()
    api.patch_get.side_effect = exceptions.APIError('foo')

    with pytest.raises(SystemExit):
        patches.action_apply(api, 1)

    captured = capsys.readouterr()

    assert captured.out == ''
    assert captured.err == 'foo\n'


def test_action_update__invalid_id(capsys):
    api = mock.Mock()
    api.patch_get.side_effect = exceptions.APIError('foo')

    with pytest.raises(SystemExit):
        patches.action_update(api, 1)

    captured = capsys.readouterr()

    assert captured.out == ''
    assert captured.err == 'foo\n'


def test_action_update(capsys):
    api = mock.Mock()
    api.patch_get.return_value = fakes.fake_patches()[0]
    api.patch_set.return_value = True

    patches.action_update(api, 1157169, 'Accepted', 'yes', '698fa7f')

    api.patch_set.assert_called_once_with(
        1157169,
        state='Accepted',
        archived='yes',
        commit_ref='698fa7f',
    )


def test_action_update__error(capsys):
    api = mock.Mock()
    api.patch_get.return_value = fakes.fake_patches()[0]
    api.patch_set.side_effect = exceptions.APIError('foo')

    with pytest.raises(SystemExit):
        patches.action_update(api, 1157169)

    api.patch_set.assert_called_once_with(
        1157169, archived=None, commit_ref=None, state=None
    )

    captured = capsys.readouterr()

    assert captured.out == ''
    assert (
        captured.err
        == """\
foo
"""
    )
