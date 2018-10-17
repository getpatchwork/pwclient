# Patchwork command line client
# Copyright (C) 2018 Stephen Finucane <stephen@that.guru>
# Copyright (C) 2008 Nate Case <ncase@xes-inc.com>
#
# SPDX-License-Identifier: GPL-2.0-or-later


def project_id_by_name(rpc, linkname):
    """Given a project short name, look up the Project ID."""
    if len(linkname) == 0:
        return 0
    projects = rpc.project_list(linkname, 0)
    for project in projects:
        if project['linkname'] == linkname:
            return project['id']
    return 0


def action_list(rpc):
    projects = rpc.project_list("", 0)
    print("%-5s %-24s %s" % ("ID", "Name", "Description"))
    print("%-5s %-24s %s" % ("--", "----", "-----------"))
    for project in projects:
        print("%-5d %-24s %s" % (project['id'],
                                 project['linkname'],
                                 project['name']))
