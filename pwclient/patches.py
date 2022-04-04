# Patchwork command line client
# Copyright (C) 2018 Stephen Finucane <stephen@that.guru>
# Copyright (C) 2008 Nate Case <ncase@xes-inc.com>
#
# SPDX-License-Identifier: GPL-2.0-or-later

import io
import os
import re
import subprocess
import sys

from .xmlrpc import xmlrpclib
from . import people
from . import projects
from . import states


def patch_id_from_hash(api, project, hash):
    patch = api.patch_get_by_project_hash(project, hash)

    if patch == {}:
        sys.stderr.write("No patch has the hash provided\n")
        sys.exit(1)

    patch_id = patch['id']
    # be super paranoid
    try:
        patch_id = int(patch_id)
    except ValueError:
        sys.stderr.write("Invalid patch ID obtained from server\n")
        sys.exit(1)
    return patch_id


def _list_patches(patches, format_str=None):
    """Dump a list of patches to stdout."""
    if format_str:
        format_field_re = re.compile("%{([a-z0-9_]+)}")

        def patch_field(matchobj):
            fieldname = matchobj.group(1)

            if fieldname == "_msgid_":
                # naive way to strip < and > from message-id
                val = str(patch["msgid"]).strip("<>")
            else:
                val = str(patch[fieldname])

            return val

        for patch in patches:
            print(format_field_re.sub(patch_field, format_str))
    else:
        print("%-7s %-12s %s" % ("ID", "State", "Name"))
        print("%-7s %-12s %s" % ("--", "-----", "----"))
        for patch in patches:
            print("%-7d %-12s %s" %
                  (patch['id'], patch['state'], patch['name']))


def action_list(
    api, project=None, submitter=None, delegate=None, state=None,
    archived=None, msgid=None, name=None, max_count=None, format_str=None,
):
    filters = {}

    if max_count:
        filters['max_count'] = max_count

    if project:
        filters['project'] = project

    if state:
        filters['state'] = state

    if archived:
        filters['archived'] = archived

    if msgid:
        filters['msgid'] = msgid

    if name:
        filters['name__icontains'] = name

    if state is not None:
        id = states.state_id_by_name(api, state)
        if id == 0:
            sys.stderr.write("Note: No State found matching %s*, "
                             "ignoring filter\n" % state)
        else:
            filters['state_id'] = id

    if project is not None:
        id = projects.project_id_by_name(api, project)
        if id == 0:
            sys.stderr.write("Note: No Project found matching %s, "
                             "ignoring filter\n" % project)
        else:
            filters['project_id'] = id

    if submitter is not None:
        ids = people.person_ids_by_name(api, submitter)
        if len(ids) == 0:
            sys.stderr.write("Note: Nobody found matching *%s*\n" %
                             submitter)
        else:
            for id in ids:
                person = api.person_get(id)
                print('Patches submitted by %s <%s>:' %
                      (person['name'], person['email']))
                filters['submitter_id'] = id
                patches = api.patch_list(filters)
                _list_patches(patches, format_str)
        return

    if delegate is not None:
        ids = people.person_ids_by_name(api, delegate)
        if len(ids) == 0:
            sys.stderr.write("Note: Nobody found matching *%s*\n" %
                             delegate)
        else:
            for id in ids:
                person = api.person_get(id)
                print('Patches delegated to %s <%s>:' %
                      (person['name'], person['email']))
                filters['delegate_id'] = id
                patches = api.patch_list(filters)
                _list_patches(patches, format_str)
        return

    patches = api.patch_list(filters)
    _list_patches(patches, format_str)


def action_info(api, patch_id):
    patch = api.patch_get(patch_id)

    if patch == {}:
        sys.stderr.write("Error getting information on patch ID %d\n" %
                         patch_id)
        sys.exit(1)

    s = "Information for patch id %d" % (patch_id)
    print(s)
    print('-' * len(s))
    for key, value in sorted(patch.items()):
        # Some values are transferred as Binary data, these are encoded in
        # utf-8. As of Python 3.9 xmlrpclib.Binary.__str__ however assumes
        # latin1, so decode explicitly
        if type(value) == xmlrpclib.Binary:
            value = str(value.data, 'utf-8')
        print("- %- 14s: %s" % (key, value))


def action_get(api, patch_id):
    patch = api.patch_get(patch_id)
    mbox = api.patch_get_mbox(patch_id)

    if patch == {} or len(mbox) == 0:
        sys.stderr.write("Unable to get patch %d\n" % patch_id)
        sys.exit(1)

    base_fname = fname = os.path.basename(patch['filename'])
    fname += '.patch'
    i = 0
    while os.path.exists(fname):
        fname = "%s.%d.patch" % (base_fname, i)
        i += 1

    with io.open(fname, 'x', encoding='utf-8') as f:
        f.write(mbox)
        print('Saved patch to %s' % fname)


def action_view(api, patch_ids):
    mboxes = []

    for patch_id in patch_ids:
        mbox = api.patch_get_mbox(patch_id)
        if mbox:
            mboxes.append(mbox)

    if not mboxes:
        return

    pager = os.environ.get('PAGER')
    if pager:
        # TODO(stephenfin): Use as a context manager when we drop support for
        # Python 2.7
        pager = subprocess.Popen(pager.split(), stdin=subprocess.PIPE)
        try:
            pager.communicate(input='\n'.join(mboxes).encode('utf-8'))
        finally:
            if pager.stdout:
                pager.stdout.close()
            if pager.stderr:
                pager.stderr.close()
            if pager.stdin:
                pager.stdin.close()
            pager.wait()
    else:
        for mbox in mboxes:
            print(mbox)


def action_apply(api, patch_id, apply_cmd=None):
    patch = api.patch_get(patch_id)
    if patch == {}:
        sys.stderr.write("Error getting information on patch ID %d\n" %
                         patch_id)
        sys.exit(1)

    if apply_cmd is None:
        print('Applying patch #%d to current directory' % patch_id)
        apply_cmd = ['patch', '-p1']
    else:
        print('Applying patch #%d using "%s"' %
              (patch_id, ' '.join(apply_cmd)))

    print('Description: %s' % patch['name'])

    mbox = api.patch_get_mbox(patch_id)
    if len(mbox) > 0:
        proc = subprocess.Popen(apply_cmd, stdin=subprocess.PIPE)
        proc.communicate(mbox.encode('utf-8'))
        return proc.returncode
    else:
        sys.stderr.write("Error: No patch content found\n")
        sys.exit(1)


def action_update(api, patch_id, state=None, archived=None, commit=None):
    patch = api.patch_get(patch_id)
    if patch == {}:
        sys.stderr.write("Error getting information on patch ID %d\n" %
                         patch_id)
        sys.exit(1)

    params = {}

    if state:
        state_id = states.state_id_by_name(api, state)
        # TODO(stephenfin): This should happen at the API layer
        if state_id == 0:
            sys.stderr.write("Error: No State found matching %s*\n" % state)
            sys.exit(1)
        params['state'] = state_id

    if commit:
        params['commit_ref'] = commit

    if archived:
        params['archived'] = archived == 'yes'

    success = False
    try:
        success = api.patch_set(patch_id, params)
    except xmlrpclib.Fault as f:
        sys.stderr.write("Error updating patch: %s\n" % f.faultString)

    if not success:
        sys.stderr.write("Patch not updated\n")
