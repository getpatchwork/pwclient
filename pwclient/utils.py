# Copyright (C) 2008 Nate Case <ncase@xes-inc.com>
# Copyright (C) 2018 Stephen Finucane <stephen@that.guru>
#
# This file is part of pwclient.
#
# pwclient is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# pwclient is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with pwclient; if not, see <http://www.gnu.org/licenses/>.

import shutil
import sys

try:
    import configparser
except ImportError:  # python 2.7
    import ConfigParser as configparser


def migrate_old_config_file(config_file, config):
    """Convert a config file to the Patchwork 1.0 format."""
    sys.stderr.write('%s is in the old format. Migrating it...' %
                     config_file)

    old_project = config.get('base', 'project')

    new_config = configparser.ConfigParser()
    new_config.add_section('options')

    new_config.set('options', 'default', old_project)
    new_config.add_section(old_project)

    new_config.set(old_project, 'url', config.get('base', 'url'))
    if config.has_option('auth', 'username'):
        new_config.set(
            old_project, 'username', config.get('auth', 'username'))
    if config.has_option('auth', 'password'):
        new_config.set(
            old_project, 'password', config.get('auth', 'password'))

    old_config_file = config_file + '.orig'
    shutil.copy2(config_file, old_config_file)

    with open(config_file, 'wb') as fd:
        new_config.write(fd)

    sys.stderr.write(' Done.\n')
    sys.stderr.write(
        'Your old %s was saved to %s\n' % (config_file, old_config_file))
    sys.stderr.write(
        'and was converted to the new format. You may want to\n')
    sys.stderr.write('inspect it before continuing.\n')
