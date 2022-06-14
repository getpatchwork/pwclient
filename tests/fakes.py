"""Generate fake data from the XML-RPC API."""


def fake_patches():
    return [
        {
            'id': 1157169,
            'date': '2000-12-31 00:11:22',
            'filename': '1-3--Drop-support-for-Python-3-4--add-Python-3-7',
            'msgid': '<20190903170304.24325-1-stephen@that.guru>',
            'name': '[1/3] Drop support for Python 3.4, add Python 3.7',
            'project': 'my-project',
            'project_id': 1,
            'state': 'New',
            'state_id': 1,
            'archived': False,
            'submitter': 'Joe Bloggs <joe.bloggs@example.com>',
            'submitter_id': 1,
            'delegate': 'admin',
            'delegate_id': 1,
            'commit_ref': '',
            'hash': '',
        },
        {
            'id': 1157170,
            'date': '2000-12-31 00:11:22',
            'filename': '2-3--docker--Simplify-MySQL-reset',
            'msgid': '<20190903170304.24325-2-stephen@that.guru>',
            'name': '[2/3] docker: Simplify MySQL reset',
            'project': 'my-project',
            'project_id': 1,
            'state': 'Accepted',
            'state_id': 3,
            'archived': False,
            'submitter': 'Joe Bloggs <joe.bloggs@example.com>',
            'submitter_id': 1,
            'delegate': 'admin',
            'delegate_id': 1,
            'commit_ref': '',
            'hash': '',
        },
        {
            'id': 1157168,
            'date': '2000-12-31 00:11:22',
            'filename': '3-3--docker--Use-pyenv-for-Python-versions',
            'msgid': '<20190903170304.24325-3-stephen@that.guru>',
            'name': '[3/3] docker: Use pyenv for Python versions',
            'project': 'my-project',
            'project_id': 1,
            'state': 'Rejected',
            'state_id': 4,
            'archived': True,
            'submitter': 'Joe Bloggs <joe.bloggs@example.com>',
            'submitter_id': 1,
            'delegate': 'admin',
            'delegate_id': 1,
            'commit_ref': '',
            'hash': '',
        },
    ]


def fake_people():
    return [
        {
            'id': 1,
            'name': 'Jeremy Kerr',
            'email': 'jk@ozlabs.org',
        },
        {
            'id': 4,
            'name': 'Michael Ellerman',
            'email': 'michael@ellerman.id.au',
        },
        {
            'id': 5,
            'name': 'Kumar Gala',
            'email': 'galak@example.com',
        },
    ]


def fake_projects():
    return [
        {
            'id': 1,
            'name': 'Patchwork',
            'linkname': 'patchwork',
            'listid': 'patchwork.lists.ozlabs.org',
            'listemail': 'patchwork@lists.ozlabs.org',
        },
    ]


def fake_checks():
    return [
        {
            'id': 1,
            'patch': 'A sample patch',
            'patch_id': 1,
            'user': 'Joe Bloggs',
            'user_id': 1,
            'state': 'success',
            'target_url': 'https://example.com/',
            'context': 'hello-world',
        },
    ]


def fake_states():
    return [
        {
            'id': 1,
            'name': 'New',
        }
    ]
