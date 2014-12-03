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


def create(name, home=None, groups=None):
    """
    Create a system user
    """
    for group in groups:
        debian.groupadd(group, gid_min=10000)
    with sudo(user='root'):
        # TODO: Use --system
        debian.useradd(name, home=home, uid_min=10000, shell='/bin/bash', groups=groups)
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
