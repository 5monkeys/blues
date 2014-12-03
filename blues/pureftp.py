"""
PureFTP Blueprint
===============

**Fabric environment:**

.. code-block:: yaml

    blueprints:
      - blues.pureftp
    settings:
      pureftp:
        users:
          - username: joe
            password: rosebud

"""
import os
from fabric.context_managers import settings
from fabric.contrib import files
from fabric.decorators import task

from refabric.context_managers import sudo
from refabric.contrib import blueprints

from . import debian
from refabric.operations import run

__all__ = ['start', 'stop', 'restart', 'setup', 'configure']


blueprint = blueprints.get(__name__)

start = debian.service_task('pure-ftpd', 'start')
stop = debian.service_task('pure-ftpd', 'stop')
restart = debian.service_task('pure-ftpd', 'restart')

ftp_home = '/srv/ftp'
ftp_user = 'ftp-data'
ftp_group = 'ftp-data'


@task
def setup():
    """
    Install and configure ProFTPD
    """
    install()
    configure()


def install():
    with sudo():
        debian.apt_get('install', 'pure-ftpd', 'openssl')
        # TODO: Use --system
        debian.groupadd(ftp_group)
        # TODO: Use --system
        debian.useradd(ftp_user, home='/dev/null', create_home=False, skeleton=False,
                       groups=[ftp_group], shell='/etc')
        debian.mkdir(ftp_home, owner=ftp_user, group=ftp_group)
        # Create user database
        run('pure-pw mkdb')
        # Set up symlinks
        debian.ln('/etc/pure-ftpd/pureftpd.passwd', '/etc/pureftpd.passwd')
        debian.ln('/etc/pure-ftpd/pureftpd.pdb', '/etc/pureftpd.pdb')
        debian.ln('/etc/pure-ftpd/conf/PureDB', '/etc/pure-ftpd/auth/PureDB')
        # Enable TLS
        run('echo 1 > /etc/pure-ftpd/conf/TLS')
        key_path = '/etc/ssl/private/pure-ftpd.pem'
        if not files.exists(key_path):
            prompts = {
                'Country Name (2 letter code) [AU]:': '',
                'State or Province Name (full name) [Some-State]:': '',
                'Locality Name (eg, city) []:': '',
                'Organization Name (eg, company) [Internet Widgits Pty Ltd]:': '',
                'Organizational Unit Name (eg, section) []:': '',
                'Common Name (e.g. server FQDN or YOUR name) []:': '',
                'Email Address []:': ''
            }
            with settings(prompts=prompts):
                run('openssl req -x509 -nodes -newkey rsa:2048 -keyout {0} -out {0}'.format(
                    key_path))
            debian.chmod(key_path, 600)
@task
def configure():
    """
    Configure ProFTPD
    """
    with sudo():
        for user in blueprint.get('users'):
            username, password = user['username'], user['password']
            if run('pure-pw show {}'.format(username)).return_code == 0:
                continue
            user_home = os.path.join(ftp_home, username)
            debian.mkdir(user_home, owner=ftp_user, group=ftp_group)
            prompts = {
                'Password: ': password,
                'Enter it again: ': password
            }
            with settings(prompts=prompts):
                run('pure-pw useradd {} -u {} -d {}'.format(username, ftp_user, user_home))
        run('pure-pw mkdb')
    restart()
