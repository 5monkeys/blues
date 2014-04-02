import os
from fabric.api import run
from fabric.context_managers import quiet
from fabric.contrib import files
from refabric.contrib import debian, templates
from refabric.context_managers import sudo
from refabric import context_managers as ctx


def create(name, home=None):
    """
    Create a system user
    """
    with sudo(user='root'):
        debian.groupadd(name, gid_min=10000)
        debian.useradd(name, gid=name, home=home, uid_min=10000, shell='/bin/bash')


def get_available_uid(min_uid=5000):
    """
    Grep UIDs from /etc/passwd and return the highest available UID.
    """
    with quiet():
        cmd = "getent passwd | grep -v nobody | awk -F: '{print $3}'"
        output = run(cmd)
    # Split output into a list of uids
    uids = output.splitlines()
    # Convert uids into ints and sort them
    uids = map(int, uids)
    max_uid = max(uids)
    if max_uid < min_uid:
        return min_uid
    else:
        return max_uid + 1


def upload_auth_keys(username, key_pair_path):
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
