"""
User Utils
==========

Debian user helpers for other blueprints to use.
"""
import os

from fabric.contrib import files

from refabric.contrib import templates
from refabric.context_managers import sudo

from . import debian


def create(name, home=None, groups=None, system=True, service=False):
    """
    Create a system user
    """
    shell = '/bin/bash'
    create_home = True
    id_min = None
    id_max = None

    if not home:
        home = '/dev/null'

    if not system:
        service = True

    if service:
        shell = '/bin/false'
        create_home = False
        id_min = 100
        id_max = 499
        system = False

    with sudo(user='root'):
        for group in groups or []:
            print 'join group', group
            debian.groupadd(group, gid_min=id_min, gid_max=id_max)

        debian.useradd(name, system=system, home=home, create_home=create_home,
                       uid_min=id_min, uid_max=id_max, shell=shell, groups=groups)
        if system:
            create_ssh_path(name)


def create_ssh_path(username):
    user = debian.get_user(username)
    ssh_path = os.path.join(user['home'], '.ssh')
    debian.mkdir(ssh_path, owner=username, group=username)
    debian.chmod(ssh_path, mode=700)


def upload_ssh_keys(username, key_pair_path):
    user = debian.get_user(username)
    ssh_path = os.path.join(user['home'], '.ssh')
    templates.upload(key_pair_path, ssh_path, user=username)
    # Ensure security
    debian.chmod(ssh_path, mode=600, owner=username, group=username, recursive=True)
    debian.chmod(ssh_path, mode=700)


def set_strict_host_checking(username, host, check=False):
    user = debian.get_user(username)
    with sudo(username):
        filename = os.path.join(user['home'], '.ssh', 'config')
        value = 'yes' if check else 'no'
        lines = [
            'Host {}'.format(host),
            '\tStrictHostKeyChecking {}'.format(value)
        ]
        files.append(filename, lines, shell=True)
