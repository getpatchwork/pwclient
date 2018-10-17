# Patchwork command line client
# Copyright (C) 2018 Stephen Finucane <stephen@that.guru>
# Copyright (C) 2008 Nate Case <ncase@xes-inc.com>
#
# SPDX-License-Identifier: GPL-2.0-or-later


def person_ids_by_name(rpc, name):
    """Given a partial name or email address, return a list of the
    person IDs that match."""
    if len(name) == 0:
        return []
    people = rpc.person_list(name, 0)
    return [x['id'] for x in people]
