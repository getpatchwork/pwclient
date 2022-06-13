#!/usr/bin/env python3
#
# Patchwork command line client
# Copyright (C) 2008 Nate Case <ncase@xes-inc.com>
#
# SPDX-License-Identifier: GPL-2.0-or-later

import os
import sys

from . import api as pw_api
from . import checks
from . import exceptions
from . import parser
from . import patches
from . import projects
from . import states
from . import utils

CONFIG_FILE = os.environ.get('PWCLIENTRC', os.path.expanduser('~/.pwclientrc'))

BACKEND_XMLRPC = 'xmlrpc'
BACKEND_REST = 'rest'
BACKENDS = (BACKEND_XMLRPC, BACKEND_REST)

auth_actions = ['check_create', 'update']


def main(argv=sys.argv[1:]):
    action_parser = parser.get_parser()

    if not argv:
        action_parser.print_help()
        sys.exit(0)

    args = action_parser.parse_args(argv)

    action = args.subcmd

    # grab settings from config files
    config = utils.configparser.ConfigParser()
    config.read([CONFIG_FILE])

    if not config.has_section('options') and os.path.exists(CONFIG_FILE):
        utils.migrate_old_config_file(CONFIG_FILE, config)
        sys.exit(1)

    if 'project' in args and args.project:
        project_str = args.project
    else:
        try:
            project_str = config.get('options', 'default')
        except (
            utils.configparser.NoSectionError,
            utils.configparser.NoOptionError,
        ):
            sys.stderr.write(
                'No default project configured in %s\n' % CONFIG_FILE
            )
            sys.exit(1)

    if not config.has_section(project_str):
        sys.stderr.write(
            'No section for project %s in %s\n' % (project_str, CONFIG_FILE)
        )
        sys.exit(1)

    if not config.has_option(project_str, 'url'):
        sys.stderr.write(
            'No URL for project %s in %s\n' % (project_str, CONFIG_FILE)
        )
        sys.exit(1)

    backend = config.get(project_str, 'backend', fallback=None)
    if backend is not None and backend not in BACKENDS:
        sys.stderr.write(
            "The 'backend' option is invalid. Expected one of: rest, xmlrpc; "
            "got: {backend}"
        )
        sys.exit(1)

    backend = backend or BACKEND_XMLRPC

    if action in auth_actions:
        if backend == 'rest':
            if not (
                config.has_option(project_str, 'username')
                and config.has_option(project_str, 'password')
            ) or config.has_option(project_str, 'token'):
                sys.stderr.write(
                    "The %s action requires authentication, but no "
                    "username/password or\n"
                    "token is configured\n" % action
                )
                sys.exit(1)
        else:
            if not (
                config.has_option(project_str, 'username')
                and config.has_option(project_str, 'password')
            ):
                sys.stderr.write(
                    "The %s action requires authentication, but no "
                    "username or password\n"
                    "is configured\n" % action
                )
                sys.exit(1)

    url = config.get(project_str, 'url')

    kwargs = {}
    if action in auth_actions:
        if config.has_option(project_str, 'token'):
            kwargs['token'] = config.get(project_str, 'token')
        else:
            kwargs['username'] = config.get(project_str, 'username')
            kwargs['password'] = config.get(project_str, 'password')

    try:
        if backend == 'rest':
            api = pw_api.REST(url, **kwargs)
        else:
            api = pw_api.XMLRPC(url, **kwargs)
    except exceptions.APIError as exc:
        sys.stderr.write(str(exc))
        sys.exit(1)

    patch_ids = args.id if 'id' in args and args.id else []
    if 'use_hashes' in args and args.use_hashes:
        patch_ids = [
            patches.patch_id_from_hash(api, project_str, x) for x in patch_ids
        ]
    else:
        try:
            patch_ids = [int(x) for x in patch_ids]
        except ValueError:
            sys.stderr.write('Patch IDs must be integers')
            sys.exit(1)

    if action == 'list' or action == 'search':
        patches.action_list(
            api,
            project=project_str,
            submitter=args.submitter,
            delegate=args.delegate,
            state=args.state,
            archived=args.archived,
            msgid=args.msgid,
            name=args.patch_name,
            max_count=args.max_count,
            format_str=args.format,
        )

    elif action.startswith('project'):
        projects.action_list(api)

    elif action.startswith('state'):
        states.action_list(api)

    elif action == 'view':
        patches.action_view(api, patch_ids)

    elif action == 'info':
        for patch_id in patch_ids:
            patches.action_info(api, patch_id)

    elif action == 'get':
        for patch_id in patch_ids:
            patches.action_get(api, patch_id)

    elif action == 'apply':
        for patch_id in patch_ids:
            ret = patches.action_apply(api, patch_id)
            if ret:
                sys.stderr.write("Apply failed with exit status %d\n" % ret)
                sys.exit(1)

    elif action == 'git_am':
        cmd = ['git', 'am']

        do_signoff = None
        if args.signoff:
            do_signoff = args.signoff
        elif config.has_option('options', 'signoff'):
            do_signoff = config.getboolean('options', 'signoff')
        elif config.has_option(project_str, 'signoff'):
            do_signoff = config.getboolean(project_str, 'signoff')

        if do_signoff:
            cmd.append('-s')

        do_three_way = None
        if args.three_way:
            do_three_way = args.three_way
        elif config.has_option('options', '3way'):
            do_three_way = config.getboolean('options', '3way')
        elif config.has_option(project_str, '3way'):
            do_three_way = config.getboolean(project_str, '3way')

        if do_three_way:
            cmd.append('-3')

        do_msg_id = None
        if args.msg_id:
            do_msg_id = args.msg_id
        elif config.has_option('options', 'msgid'):
            do_msg_id = config.getboolean('options', 'msgid')
        elif config.has_option(project_str, 'msgid'):
            do_msg_id = config.getboolean(project_str, 'msgid')

        if do_msg_id:
            cmd.append('-m')

        for patch_id in patch_ids:
            ret = patches.action_apply(api, patch_id, cmd)
            if ret:
                sys.stderr.write("'git am' failed with exit status %d\n" % ret)
                sys.exit(1)

    elif action == 'update':
        if args.commit_ref and len(patch_ids) > 1:
            # update multiple IDs with a single commit-hash does not make sense
            sys.stderr.write(
                'Declining update with COMMIT-REF on multiple IDs'
            )
            sys.exit(1)

        if not any([args.state, args.archived]):
            sys.stderr.write(
                'Must specify one or more update options (-a or -s)\n'
            )
            sys.exit(1)

        for patch_id in patch_ids:
            patches.action_update(
                api,
                patch_id,
                state=args.state,
                archived=args.archived,
                commit_ref=args.commit_ref,
            )

    elif action == 'check_get':
        format_str = args.format
        for patch_id in patch_ids:
            checks.action_get(api, patch_id, format_str)

    elif action == 'check_list':
        checks.action_list(api, args.patch_id, args.user)

    elif action == 'check_info':
        patch_id = args.patch_id
        check_id = args.check_id
        checks.action_info(api, patch_id, check_id)

    elif action == 'check_create':
        for patch_id in patch_ids:
            checks.action_create(
                api,
                patch_id,
                args.context,
                args.state,
                args.target_url,
                args.description,
            )


if __name__ == "__main__":
    try:
        main()
    except (UnicodeEncodeError, UnicodeDecodeError):
        import traceback

        traceback.print_exc()
        sys.stderr.write(
            'Try exporting the LANG or LC_ALL env vars. See '
            'pwclient --help for more details.\n'
        )
        sys.exit(1)
