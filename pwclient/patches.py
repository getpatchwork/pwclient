# Patchwork command line client
# Copyright (C) 2018 Stephen Finucane <stephen@that.guru>
# Copyright (C) 2008 Nate Case <ncase@xes-inc.com>
#
# SPDX-License-Identifier: GPL-2.0-or-later

import itertools
import os
import re
import subprocess
import sys


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
        print("ID      State        Name")
        print("--      -----        ----")
        for patch in patches:
            print(f"{patch['id']:<7} {patch['state']:<12} {patch['name']}")


def action_list(
    api,
    project=None,
    submitter=None,
    delegate=None,
    state=None,
    archived=None,
    msgid=None,
    name=None,
    hash=None,
    max_count=None,
    format_str=None,
):
    # We exclude submitter and delegate since these are handled specially
    filters = {
        'project': project,
        'state': state,
        'archived': archived,
        'msgid': msgid,
        'name': name,
        'hash': hash,
        'max_count': max_count,
        'submitter': None,
        'delegate': None,
    }

    # TODO(stephenfin): Remove these logs since they break our ability to
    # filter on both submitter and delegate

    if submitter is not None:
        filters['submitter'] = submitter

        patches = api.patch_list(**filters)
        patches.sort(key=lambda x: x['submitter'])

        for person, person_patches in itertools.groupby(
            patches, key=lambda x: x['submitter']
        ):
            print(f'Patches submitted by {person}:')
            _list_patches(list(person_patches), format_str)

        return

    if delegate is not None:
        filters['delegate'] = delegate

        patches = api.patch_list(**filters)
        patches.sort(key=lambda x: x['delegate'])

        for delegate, delegate_patches in itertools.groupby(
            patches, key=lambda x: x['delegate']
        ):
            print(f'Patches delegated to {delegate}:')
            _list_patches(list(delegate_patches), format_str)

        return

    patches = api.patch_list(**filters)
    _list_patches(patches, format_str)


def action_info(api, patch_id):
    try:
        patch = api.patch_get(patch_id)
    except Exception as exc:
        print(str(exc), file=sys.stderr)
        sys.exit(1)

    s = f"Information for patch id {patch_id}"
    print(s)
    print('-' * len(s))
    for key, value in sorted(patch.items()):
        if value != '':
            print(f"- {key:<14}: {value}")
        else:
            print(f"- {key:<14}:")


def action_get(api, patch_id):
    try:
        mbox, filename = api.patch_get_mbox(patch_id)
    except Exception as exc:
        print(str(exc), file=sys.stderr)
        sys.exit(1)

    base_fname = fname = os.path.basename(filename)
    fname += '.patch'
    i = 0
    while os.path.exists(fname):
        fname = f"{base_fname}.{i}.patch"
        i += 1

    with open(fname, 'x', encoding='utf-8') as f:
        f.write(mbox)
        print(f'Saved patch to {fname}')


def action_view(api, patch_ids):
    mboxes = []

    for patch_id in patch_ids:
        try:
            mbox, _ = api.patch_get_mbox(patch_id)
        except Exception:  # noqa
            # TODO(stephenfin): We skip this for historical reasons, but should
            # we log/raise an error?
            continue

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
    try:
        patch = api.patch_get(patch_id)
    except Exception as exc:
        print(str(exc), file=sys.stderr)
        sys.exit(1)

    if apply_cmd is None:
        print(f'Applying patch #{patch_id} to current directory')
        apply_cmd = ['patch', '-p1']
    else:
        _cmd = ' '.join(apply_cmd)
        print(f'Applying patch #{patch_id} using "{_cmd}"')

    print(f"Description: {patch['name']}")

    try:
        mbox, _ = api.patch_get_mbox(patch_id)
    except Exception as exc:
        print(str(exc), file=sys.stderr)
        sys.exit(1)

    proc = subprocess.Popen(apply_cmd, stdin=subprocess.PIPE)
    proc.communicate(mbox.encode('utf-8'))
    return proc.returncode


def action_update(api, patch_id, state=None, archived=None, commit_ref=None):
    # ensure the patch actually exists first
    try:
        api.patch_get(patch_id)
    except Exception as exc:
        print(str(exc), file=sys.stderr)
        sys.exit(1)

    try:
        api.patch_set(
            patch_id,
            state=state,
            archived=archived,
            commit_ref=commit_ref,
        )
    except Exception as exc:
        print(str(exc), file=sys.stderr)
        sys.exit(1)
