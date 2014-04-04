import os
from fabric.contrib import files
from refabric.contrib import debian, blueprints, templates
from refabric.context_managers import sudo

blueprint = blueprints.get(__name__)


def create(name, home=None):
    """
    Create a system user
    """
    with sudo(user='root'):
        debian.groupadd(name, gid_min=10000)
        debian.useradd(name, gid=name, home=home, uid_min=10000, shell='/bin/bash')
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
