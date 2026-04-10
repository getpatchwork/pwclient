# Patchwork command line client
# Copyright (C) 2026 Andrea Cervesato <andrea.cervesato@suse.com>
#
# SPDX-License-Identifier: GPL-2.0-or-later

import re


def action_list(api, project=None, category=None, since=None, format_str=None):
    events = api.event_list(project=project, category=category, since=since)

    if format_str:
        format_field_re = re.compile('%{([a-z0-9_]+)}')

        def event_field(matchobj):
            fieldname = matchobj.group(1)
            return str(event[fieldname])

        for event in events:
            print(format_field_re.sub(event_field, format_str))
    else:
        print("%-10s %-24s %-24s %s" % ("ID", "Category", "Date", "Series"))
        print("%-10s %-24s %-24s %s" % ("--", "--------", "----", "------"))
        for event in events:
            print(
                "%-10d %-24s %-24s %s"
                % (
                    event['id'],
                    event['category'],
                    event['date'],
                    event.get('series_name', ''),
                )
            )
