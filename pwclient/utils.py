# Patchwork command line client
# Copyright (C) 2018 Stephen Finucane <stephen@that.guru>
# Copyright (C) 2008 Nate Case <ncase@xes-inc.com>
#
# SPDX-License-Identifier: GPL-2.0-or-later

import configparser
import shutil
import sys


def migrate_old_config_file(config_file, config):
    """Convert a config file to the Patchwork 1.0 format."""
    sys.stderr.write(f'{config_file} is in the old format. Migrating it...')

    old_project = config.get('base', 'project')

    new_config = configparser.ConfigParser()
    new_config.add_section('options')

    new_config.set('options', 'default', old_project)
    new_config.add_section(old_project)

    new_config.set(old_project, 'url', config.get('base', 'url'))
    if config.has_option('auth', 'username'):
        new_config.set(old_project, 'username', config.get('auth', 'username'))
    if config.has_option('auth', 'password'):
        new_config.set(old_project, 'password', config.get('auth', 'password'))

    old_config_file = config_file + '.orig'
    shutil.copy2(config_file, old_config_file)

    with open(config_file, 'w') as fd:
        new_config.write(fd)

    sys.stderr.write(' Done.\n')
    sys.stderr.write(
        f'Your old {config_file} was saved to {old_config_file}\n'
    )
    sys.stderr.write('and was converted to the new format. You may want to\n')
    sys.stderr.write('inspect it before continuing.\n')


if __name__ == '__main__':
    config = configparser.ConfigParser()
    config.read(sys.argv[1])

    migrate_old_config_file(sys.argv[1], config)
