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

from refabric.context_managers import sudo, silent
from refabric.contrib import blueprints

from . import debian
from . import user
from refabric.operations import run

__all__ = ['start', 'stop', 'restart', 'setup', 'configure']


blueprint = blueprints.get(__name__)

start = debian.service_task('pure-ftpd', 'start')
stop = debian.service_task('pure-ftpd', 'stop')
restart = debian.service_task('pure-ftpd', 'restart')

ftp_root = '/srv/ftp'
ftp_user = 'ftp'
ftp_group = 'www-data'


@task
def setup():
    """
    Install and configure PureFTP
    """
    install()
    configure()


def install():
    with sudo():
        debian.apt_get('install', 'pure-ftpd', 'openssl')

        # Create ftp user
        debian.useradd(ftp_user, '/dev/null', shell='/bin/false',
                       user_group=True, groups=[ftp_group], uid_min=1000)

        # Create ftp root dir
        debian.mkdir(ftp_root, mode=1770, owner=ftp_user, group=ftp_group)

        # Set up symlinks
        debian.ln('/etc/pure-ftpd/conf/PureDB', '/etc/pure-ftpd/auth/PureDB')

        # Setup umask
        umask = blueprint.get('umask')
        if umask:
            run('echo {} > /etc/pure-ftpd/conf/Umask'.format(umask.replace(':', ' ')))

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
    Configure PureFTP
    """
    with sudo():
        # Echo configurations
        setup_config()

        for user in blueprint.get('users'):
            username, password = user['username'], user['password']
            if 'homedir' in user:
                user_home = user['homedir']
            else:
                user_home = os.path.join(ftp_root, username)

            passwd_path = '/etc/pure-ftpd/pureftpd.passwd'
            with settings(warn_only=True):
                if files.exists(passwd_path) and run('pure-pw show {}'.format(
                                                     username)).return_code == 0:
                    continue
            debian.mkdir(user_home, owner=ftp_user, group=ftp_group)
            prompts = {
                'Password: ': password,
                'Enter it again: ': password
            }
            with settings(prompts=prompts):
                run('pure-pw useradd {} -u {} -g {} -d {}'.format(username, ftp_user, ftp_group,
                                                                  user_home))
        run('pure-pw mkdb')
    restart()


config_defaults = {
    'ChrootEveryone': 'yes',  # Cage in every user in his home directory
    'BrokenClientsCompatibility': 'yes',  # Turn on compatibility hacks for broken clients
    'MaxClientsNumber': '50',  # Maximum number of simultaneous users
    'MaxClientsPerIP': '5',  # Maximum number of sim clients with the same IP address
    'Daemonize': 'yes',  # Fork in background
    'VerboseLog': 'yes',  # Turn off verbose logging
    'DisplayDotFiles': 'yes',  # List dot-files even when the client doesn't send "-a".
    'ProhibitDotFilesWrite': 'yes',  # Users can't delete/write files beginning with a dot ('.')
    'NoChmod': 'yes',  # Disallow the CHMOD command. Users can't change perms of their files.
    'AnonymousOnly': 'no',  # Don't allow authenticated users - have a public anonymous FTP only.
    'NoAnonymous': 'yes',  # Don't allow authenticated users - have a public anonymous FTP only.
    'PAMAuthentication': 'no',  # Disable PAM authentication
    'UnixAuthentication': 'no',  # Disable /etc/passwd (UNIX) authentication
    'DontResolve': 'yes',  # Don't resolve host names in log files.
    'MaxIdleTime': '15',  # Maximum idle time in minutes (default = 15 minutes)
    'LimitRecursion': '2000 8',  # 'ls' recursion limits.
    'AntiWarez': 'yes',  # Disallow downloading of files owned by "ftp"
    'AnonymousCanCreateDirs': 'no',  # Are anonymous users allowed to create new directories ?
    'MaxLoad': '6',  # If the system is more loaded than the following value, disallow download.
    'AllowUserFXP': 'no',  # Disallow FXP transfers for authenticated users.
    'AllowAnonymousFXP': 'no',  # Disallow anonymous FXP for anonymous and non-anonymous users.
    'AutoRename': 'no',  # Turn off autorenaming of conflicting filenames
    'AnonymousCantUpload': 'yes',  # Disallow anonymous users to upload new files (no = upload is allowed)
    'NoChmod': 'yes',  # Disallow the CHMOD command. Users can't change perms of their files.
    'MaxDiskUsage': '80',  # When the partition is more that X percent full, new uploads are disallowed.
    'CustomerProof': 'yes',  # Workaround against common customer mistakes like chmod 0 public_html
    'PureDB': '/etc/pure-ftpd/pureftpd.pdb'  # User database
}


def set_pureftp_config_value(**kwargs):
    for key, value in kwargs.iteritems():
        run("echo '{}' > /etc/pure-ftpd/conf/{}".format(value, key))


def setup_config():
    with silent():
        config = config_defaults.copy()
        config.update(blueprint.get(''))
        set_pureftp_config_value(**config_defaults)
