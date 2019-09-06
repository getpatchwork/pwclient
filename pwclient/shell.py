#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Patchwork command line client
# Copyright (C) 2008 Nate Case <ncase@xes-inc.com>
#
# SPDX-License-Identifier: GPL-2.0-or-later

from __future__ import print_function
from __future__ import unicode_literals

import os
import sys

from . import checks
from . import parser
from . import patches
from . import projects
from . import states
from . import utils
from . import xmlrpc


CONFIG_FILE = os.path.expanduser('~/.pwclientrc')

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
        except (utils.configparser.NoSectionError,
                utils.configparser.NoOptionError):
            sys.stderr.write(
                'No default project configured in %s\n' % CONFIG_FILE)
            sys.exit(1)

    if not config.has_section(project_str):
        sys.stderr.write(
            'No section for project %s in %s\n' % (project_str, CONFIG_FILE))
        sys.exit(1)

    if not config.has_option(project_str, 'url'):
        sys.stderr.write(
            'No URL for project %s in %s\n' % (project_str, CONFIG_FILE))
        sys.exit(1)

    if action in auth_actions:
        if not (config.has_option(project_str, 'username') and
                config.has_option(project_str, 'password')):
            sys.stderr.write("The %s action requires authentication, but no "
                             "username or password\nis configured\n" % action)
            sys.exit(1)

    url = config.get(project_str, 'url')

    transport = xmlrpc.Transport(url)
    if action in auth_actions:
        transport.set_credentials(
            config.get(project_str, 'username'),
            config.get(project_str, 'password'))

    try:
        rpc = xmlrpc.xmlrpclib.Server(url, transport=transport)
    except (IOError, OSError):
        sys.stderr.write("Unable to connect to %s\n" % url)
        sys.exit(1)

    patch_ids = args.id if 'id' in args and args.id else []
    if 'use_hashes' in args and args.use_hashes:
        patch_ids = [
            patches.patch_id_from_hash(rpc, project_str, x) for x in patch_ids]
    else:
        try:
            patch_ids = [int(x) for x in patch_ids]
        except ValueError:
            sys.stderr.write('Patch IDs must be integers')
            sys.exit(1)

    if action == 'list' or action == 'search':
        filt = patches.Filter()

        if args.n:
            filt.add('max_count', args.n)

        if args.N:
            filt.add('max_count', 0 - args.N)

        if project_str:
            filt.add('project', project_str)

        if args.state:
            filt.add('state', args.state)

        if args.archived:
            filt.add('archived', args.archived == 'yes')

        if args.msgid:
            filt.add('msgid', args.msgid)

        if args.patch_name:
            filt.add('name__icontains', args.patch_name)

        submitter_str = args.submitter
        delegate_str = args.delegate
        format_str = args.format

        patches.action_list(rpc, filt, submitter_str, delegate_str, format_str)

    elif action.startswith('project'):
        projects.action_list(rpc)

    elif action.startswith('state'):
        states.action_list(rpc)

    elif action == 'view':
        patches.action_view(rpc, patch_ids)

    elif action == 'info':
        for patch_id in patch_ids:
            patches.action_info(rpc, patch_id)

    elif action == 'get':
        for patch_id in patch_ids:
            patches.action_get(rpc, patch_id)

    elif action == 'apply':
        for patch_id in patch_ids:
            ret = patches.action_apply(rpc, patch_id)
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

        for patch_id in patch_ids:
            ret = patches.action_apply(rpc, patch_id, cmd)
            if ret:
                sys.stderr.write("'git am' failed with exit status %d\n" % ret)
                sys.exit(1)

    elif action == 'update':
        if args.commit_ref and len(patch_ids) > 1:
            # update multiple IDs with a single commit-hash does not make sense
            sys.stderr.write(
                'Declining update with COMMIT-REF on multiple IDs')
            sys.exit(1)

        if not any([args.state, args.archived]):
            sys.stderr.write(
                'Must specify one or more update options (-a or -s)\n')
            sys.exit(1)

        for patch_id in patch_ids:
            patches.action_update(
                rpc, patch_id, state=args.state, archived=args.archived,
                commit=args.commit_ref)

    elif action == 'check_list':
        checks.action_list(rpc)

    elif action == 'check_info':
        check_id = args.check_id
        checks.action_info(rpc, check_id)

    elif action == 'check_create':
        for patch_id in patch_ids:
            checks.action_create(
                rpc, patch_id, args.context, args.state, args.target_url,
                args.description)


if __name__ == "__main__":
    try:
        main()
    except (UnicodeEncodeError, UnicodeDecodeError):
        import traceback
        traceback.print_exc()
        sys.stderr.write('Try exporting the LANG or LC_ALL env vars. See '
                         'pwclient --help for more details.\n')
        sys.exit(1)
