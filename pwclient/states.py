# Patchwork command line client
# Copyright (C) 2018 Stephen Finucane <stephen@that.guru>
# Copyright (C) 2008 Nate Case <ncase@xes-inc.com>
#
# SPDX-License-Identifier: GPL-2.0-or-later


def action_list(api):
    states = api.state_list("", 0)
    print("%-5s %s" % ("ID", "Name"))
    print("%-5s %s" % ("--", "----"))
    for state in states:
        print("%-5d %s" % (state['id'], state['name']))
