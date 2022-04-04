# Patchwork command line client
# Copyright (C) 2018 Stephen Finucane <stephen@that.guru>
# Copyright (C) 2008 Nate Case <ncase@xes-inc.com>
#
# SPDX-License-Identifier: GPL-2.0-or-later


def action_list(api):
    projects = api.project_list("", 0)
    print("%-5s %-24s %s" % ("ID", "Name", "Description"))
    print("%-5s %-24s %s" % ("--", "----", "-----------"))
    for project in projects:
        print(
            "%-5d %-24s %s"
            % (project['id'], project['linkname'], project['name'])
        )
