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
import subprocess

from . import checks
from . import parser
from . import patches
from . import projects
from . import states
from . import utils
from . import xmlrpc


# Default Patchwork remote XML-RPC server URL
# This script will check the PW_XMLRPC_URL environment variable
# for the URL to access.  If that is unspecified, it will fallback to
# the hardcoded default value specified here.
DEFAULT_URL = "http://patchwork/xmlrpc/"
CONFIG_FILE = os.path.expanduser('~/.pwclientrc')

auth_actions = ['check_create', 'update']


def main(argv=sys.argv[1:]):
    action_parser = parser.get_parser()

    if not argv:
        action_parser.print_help()
        sys.exit(0)

    args = action_parser.parse_args(argv)
    args = dict(vars(args))
    action = args.get('subcmd')

    # set defaults
    filt = patches.Filter()
    commit_str = None
    url = DEFAULT_URL

    use_hashes = args.get('h')
    archived_str = args.get('a')
    state_str = args.get('s')
    project_str = args.get('p')
    submitter_str = args.get('w')
    delegate_str = args.get('d')
    format_str = args.get('f')
    patch_ids = args.get('id') or []
    msgid_str = args.get('m')
    commit_str = args.get('c')

    # update multiple IDs with a single commit-hash does not make sense
    if commit_str and len(patch_ids) > 1 and action == 'update':
        sys.stderr.write("Declining update with COMMIT-REF on multiple IDs")
        sys.exit(1)

    if state_str is None and archived_str is None and action == 'update':
        sys.stderr.write(
            'Must specify one or more update options (-a or -s)\n')
        sys.exit(1)

    if args.get('n'):
        filt.add('max_count', args.get('n'))

    if args.get('N'):
        filt.add('max_count', 0 - args.get('N'))

    do_signoff = args.get('signoff')
    do_three_way = args.get('3way')

    # grab settings from config files
    config = utils.configparser.ConfigParser()
    config.read([CONFIG_FILE])

    if not config.has_section('options') and os.path.exists(CONFIG_FILE):
        utils.migrate_old_config_file(CONFIG_FILE, config)
        sys.exit(1)

    if not project_str:
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

    if not do_signoff and config.has_option('options', 'signoff'):
        do_signoff = config.getboolean('options', 'signoff')
    if not do_signoff and config.has_option(project_str, 'signoff'):
        do_signoff = config.getboolean(project_str, 'signoff')
    if not do_three_way and config.has_option('options', '3way'):
        do_three_way = config.getboolean('options', '3way')
    if not do_three_way and config.has_option(project_str, '3way'):
        do_three_way = config.getboolean(project_str, '3way')

    url = config.get(project_str, 'url')

    transport = xmlrpc.Transport(url)
    if action in auth_actions:
        if config.has_option(project_str, 'username') and \
                config.has_option(project_str, 'password'):
            transport.set_credentials(
                config.get(project_str, 'username'),
                config.get(project_str, 'password'))
        else:
            sys.stderr.write("The %s action requires authentication, but no "
                             "username or password\nis configured\n" % action)
            sys.exit(1)

    if project_str:
        filt.add("project", project_str)

    if state_str:
        filt.add("state", state_str)

    if archived_str:
        filt.add("archived", archived_str == 'yes')

    if msgid_str:
        filt.add("msgid", msgid_str)

    try:
        rpc = xmlrpc.xmlrpclib.Server(url, transport=transport)
    except (IOError, OSError):
        sys.stderr.write("Unable to connect to %s\n" % url)
        sys.exit(1)

    if use_hashes:
        patch_ids = [
            patches.patch_id_from_hash(rpc, project_str, x) for x in patch_ids]
    else:
        try:
            patch_ids = [int(x) for x in patch_ids]
        except ValueError:
            sys.stderr.write('Patch IDs must be integers')
            sys.exit(1)

    if action == 'list' or action == 'search':
        if args.get('patch_name') is not None:
            filt.add("name__icontains", args.get('patch_name'))
        patches.action_list(rpc, filt, submitter_str, delegate_str, format_str)

    elif action.startswith('project'):
        projects.action_list(rpc)

    elif action.startswith('state'):
        states.action_list(rpc)

    elif action == 'view':
        pager = os.environ.get('PAGER')
        if pager:
            pager = subprocess.Popen(
                pager.split(), stdin=subprocess.PIPE
            )
        if pager:
            i = list()
            for patch_id in patch_ids:
                s = rpc.patch_get_mbox(patch_id)
                if len(s) > 0:
                    i.append(s)
            if len(i) > 0:
                pager.communicate(input="\n".join(i).encode("utf-8"))
            pager.stdin.close()
        else:
            for patch_id in patch_ids:
                s = rpc.patch_get_mbox(patch_id)
                if len(s) > 0:
                    print(s)

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
        if do_signoff:
            cmd.append('-s')
        if do_three_way:
            cmd.append('-3')
        for patch_id in patch_ids:
            ret = patches.action_apply(rpc, patch_id, cmd)
            if ret:
                sys.stderr.write("'git am' failed with exit status %d\n" % ret)
                sys.exit(1)

    elif action == 'update':
        for patch_id in patch_ids:
            patches.action_update(
                rpc, patch_id, state=state_str, archived=archived_str,
                commit=commit_str)

    elif action == 'check_list':
        checks.action_list(rpc)

    elif action == 'check_info':
        check_id = args['check_id']
        checks.action_info(rpc, check_id)

    elif action == 'check_create':
        for patch_id in patch_ids:
            checks.action_create(
                rpc, patch_id, args['c'], args['s'], args['u'], args['d'])


if __name__ == "__main__":
    try:
        main()
    except (UnicodeEncodeError, UnicodeDecodeError):
        import traceback
        traceback.print_exc()
        sys.stderr.write('Try exporting the LANG or LC_ALL env vars. See '
                         'pwclient --help for more details.\n')
        sys.exit(1)
