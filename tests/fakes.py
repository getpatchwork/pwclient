"""Generate fake data from the XML-RPC API."""


def fake_patches():
    return [
        {
            'id': 1157169,
            'msgid': '<20190903170304.24325-1-stephen@that.guru>',
            'name': '[1/3] Drop support for Python 3.4, add Python 3.7',
            'state': 'New',
            'filename': '1-3--Drop-support-for-Python-3-4--add-Python-3-7',
        },
        {
            'id': 1157170,
            'msgid': '<20190903170304.24325-2-stephen@that.guru>',
            'name': '[2/3] docker: Simplify MySQL reset',
            'state': 'Accepted',
            'filename': '2-3--docker--Simplify-MySQL-reset',
        },
        {
            'id': 1157168,
            'msgid': '<20190903170304.24325-3-stephen@that.guru>',
            'name': '[3/3] docker: Use pyenv for Python versions',
            'state': 'Rejected',
            'filename': '3-3--docker--Use-pyenv-for-Python-versions',
        }
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
            'context': 'hello-world',
            'state': 'success',
            'patch': 1,
        },
    ]


def fake_states():
    return [
        {
            'id': 1,
            'name': 'New',
        }
    ]
