# Patchwork command line client
# Copyright (C) 2018 Stephen Finucane <stephen@that.guru>
# Copyright (C) 2008 Nate Case <ncase@xes-inc.com>
#
# SPDX-License-Identifier: GPL-2.0-or-later


def state_id_by_name(rpc, name):
    """Given a partial state name, look up the state ID."""
    if len(name) == 0:
        return 0
    states = rpc.state_list(name, 0)
    for state in states:
        if state['name'].lower().startswith(name.lower()):
            return state['id']
    return 0


def action_list(rpc):
    states = rpc.state_list("", 0)
    print("%-5s %s" % ("ID", "Name"))
    print("%-5s %s" % ("--", "----"))
    for state in states:
        print("%-5d %s" % (state['id'], state['name']))
