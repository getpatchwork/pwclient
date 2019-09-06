# Patchwork command line client
# Copyright (C) 2018 Stephen Finucane <stephen@that.guru>
# Copyright (C) 2008 Nate Case <ncase@xes-inc.com>
#
# SPDX-License-Identifier: GPL-2.0-or-later

import argparse


def _get_hash_parser():
    hash_parser = argparse.ArgumentParser(add_help=False)
    hash_parser.add_argument(
        '-h', '--use-hashes', action='store_true',
        help="lookup by patch hash")
    hash_parser.add_argument(
        '-p', '--project', metavar='PROJECT',
        help="lookup patch in project")
    hash_parser.add_argument(
        'id', metavar='PATCH_ID', nargs='+', action='store', default=[],
        help="patch ID")

    return hash_parser


def _get_filter_parser():
    filter_parser = argparse.ArgumentParser(add_help=False)
    filter_parser.add_argument(
        '-s', '--state', metavar='STATE',
        help="filter by patch state (e.g., 'New', 'Accepted', etc.)")
    filter_parser.add_argument(
        '-a', '--archived', choices=['yes', 'no'],
        help="filter by patch archived state")
    filter_parser.add_argument(
        '-p', '--project', metavar='PROJECT',
        help="filter by project name (see 'projects' for list)")
    filter_parser.add_argument(
        '-w', '--submitter', metavar='WHO',
        help="filter by submitter (name, e-mail substring search)")
    filter_parser.add_argument(
        '-d', '--delegate', metavar='WHO',
        help="filter by delegate (name, e-mail substring search)")
    filter_parser.add_argument(
        '-n', metavar='MAX#', type=int,
        help="limit results to first n")
    filter_parser.add_argument(
        '-N', metavar='MAX#', type=int,
        help="limit results to last N")
    filter_parser.add_argument(
        '-m', '--msgid', metavar='MESSAGEID',
        help="filter by Message-Id")
    filter_parser.add_argument(
        '-f', '--format', metavar='FORMAT',
        help=("print output in the given format. You can use tags matching "
              "fields, e.g. %%{id}, %%{state}, or %%{msgid}."))
    filter_parser.add_argument(
        'patch_name', metavar='STR', nargs='?',
        help='substring to search for patches by name')

    return filter_parser


def get_parser():
    hash_parser = _get_hash_parser()
    filter_parser = _get_filter_parser()

    action_parser = argparse.ArgumentParser(
        prog='pwclient',
        formatter_class=argparse.RawTextHelpFormatter,
        epilog="""Use 'pwclient <command> --help' for more info.

To avoid unicode encode/decode errors, you should export the LANG or LC_ALL
environment variables according to the configured locales on your system. If
these variables are already set, make sure that they point to valid and
installed locales.
""",
    )

    subparsers = action_parser.add_subparsers(title='Commands')

    apply_parser = subparsers.add_parser(
        'apply', parents=[hash_parser], conflict_handler='resolve',
        help="apply a patch in the current directory using 'patch -p1'")
    apply_parser.set_defaults(subcmd='apply')

    git_am_parser = subparsers.add_parser(
        'git-am', parents=[hash_parser], conflict_handler='resolve',
        help="apply a patch to current git branch using 'git am'")
    git_am_parser.add_argument(
        '-s', '--signoff', action='store_true',
        help="pass '--signoff' to 'git-am'")
    git_am_parser.add_argument(
        '-3', '--3way', action='store_true', dest='three_way',
        help="pass '--3way' to 'git-am'")
    git_am_parser.set_defaults(subcmd='git_am')

    get_parser = subparsers.add_parser(
        'get', parents=[hash_parser], conflict_handler='resolve',
        help="download a patch and save it locally")
    get_parser.set_defaults(subcmd='get')

    info_parser = subparsers.add_parser(
        'info', parents=[hash_parser], conflict_handler='resolve',
        help="show information for a given patch ID")
    info_parser.set_defaults(subcmd='info')

    projects_parser = subparsers.add_parser(
        'projects',
        help="list all projects")
    projects_parser.set_defaults(subcmd='projects')

    check_list_parser = subparsers.add_parser(
        'check-list', add_help=False,
        help="list all checks"
    )
    check_list_parser.set_defaults(subcmd='check_list')

    check_info_parser = subparsers.add_parser(
        'check-info', add_help=False,
        help="show information for a given check")
    check_info_parser.add_argument(
        'check_id', metavar='ID', action='store', type=int,
        help="check ID")
    check_info_parser.set_defaults(subcmd='check_info')

    check_create_parser = subparsers.add_parser(
        'check-create', parents=[hash_parser], conflict_handler='resolve',
        help="add a check to a patch")
    check_create_parser.add_argument(
        '-c', '--context', metavar='CONTEXT')
    check_create_parser.add_argument(
        '-s', '--state', choices=('pending', 'success', 'warning', 'fail'))
    check_create_parser.add_argument(
        '-u', '--target-url', metavar='TARGET_URL', default='')
    check_create_parser.add_argument(
        '-d', '--description', metavar='DESCRIPTION', default='')
    check_create_parser.set_defaults(subcmd='check_create')

    states_parser = subparsers.add_parser(
        'states',
        help="show list of potential patch states")
    states_parser.set_defaults(subcmd='states')

    view_parser = subparsers.add_parser(
        'view', parents=[hash_parser], conflict_handler='resolve',
        help="view a patch")
    view_parser.set_defaults(subcmd='view')

    update_parser = subparsers.add_parser(
        'update', parents=[hash_parser], conflict_handler='resolve',
        help="update patch",
        epilog="using a COMMIT-REF allows for only one ID to be specified")
    update_parser.add_argument(
        '-c', '--commit-ref', metavar='COMMIT-REF',
        help="commit reference hash")
    update_parser.add_argument(
        '-s', '--state', metavar='STATE',
        help="set patch state (e.g., 'Accepted', 'Superseded' etc.)")
    update_parser.add_argument(
        '-a', '--archived', choices=['yes', 'no'],
        help="set patch archived state")
    update_parser.set_defaults(subcmd='update')

    list_parser = subparsers.add_parser(
        'list', parents=[filter_parser],
        help='list patches using optional filters')
    list_parser.set_defaults(subcmd='list')

    # Poor man's argparse aliases: we register the "search" parser but
    # effectively use "list" for the help-text.
    search_parser = subparsers.add_parser(
        'search', parents=[filter_parser],
        help="alias for 'list'")
    search_parser.set_defaults(subcmd='list')

    return action_parser
