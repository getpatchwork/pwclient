# Patchwork command line client
# Copyright (C) 2018 Stephen Finucane <stephen@that.guru>
# Copyright (C) 2008 Nate Case <ncase@xes-inc.com>
#
# SPDX-License-Identifier: GPL-2.0-or-later

import sys

from pwclient.xmlrpc import xmlrpclib


def action_list(rpc):
    checks = rpc.check_list()
    print("%-5s %-16s %-8s %s" % ("ID", "Context", "State", "Patch"))
    print("%-5s %-16s %-8s %s" % ("--", "-------", "-----", "-----"))
    for check in checks:
        print("%-5s %-16s %-8s %s" % (check['id'],
                                      check['context'],
                                      check['state'],
                                      check['patch']))


def action_info(rpc, check_id):
    check = rpc.check_get(check_id)
    s = "Information for check id %d" % (check_id)
    print(s)
    print('-' * len(s))
    for key, value in sorted(check.items()):
        print("- %- 14s: %s" % (key, value))


def action_create(rpc, patch_id, context, state, url, description):
    try:
        rpc.check_create(patch_id, context, state, url, description)
    except xmlrpclib.Fault as f:
        sys.stderr.write("Error creating check: %s\n" % f.faultString)
