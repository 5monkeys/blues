"""
Node.js Blueprint
=================

**Fabric environment:**

.. code-block:: yaml

    blueprints:
      - blues.node

    settings:
      node:
        # version: latest    # Install latest node version
        packages:            # List of npm packages to install (Optional)
          # - coffee-script
          # - yuglify
          # - less

"""
from contextlib import contextmanager
from fabric.context_managers import cd, prefix
from fabric.decorators import task
from fabric.utils import abort

from refabric.api import run, info
from refabric.context_managers import sudo
from refabric.contrib import blueprints

from .util import maybe_managed

from . import debian

__all__ = ['setup', 'configure']


blueprint = blueprints.get(__name__)


@task
def setup():
    """
    Setup Nodejs
    """
    install()
    configure()


@task
def configure():
    """
    Install npm packages
    """
    install_packages()


def get_version():
    return blueprint.get('version')


def install(for_user=None):
    version = get_version()

    if version == 'latest':
        info('Installing latest node from tarball', )
        with sudo():
            install_node_build_deps()

        if for_user is not None:
            cm = sudo(user=for_user)
        else:
            cm = None

        with maybe_managed(cm):
            return install_latest()

    else:
        info('Installing node from apt')
        return install_deb()


def install_node_build_deps():
    info('Installing build tools')
    debian.apt_get('update')
    debian.apt_get('install', 'build-essential node-rimraf')


def install_latest():
    info('Installing latest node and NPM for {user}', user=run('whoami').stdout)

    common = [
        'set -x',
        'set -o verbose',
        'eval PREFIX=~/.local',
        'eval PROFILE=~/.bash_profile',
        'eval SRC=~/node-latest-install',
        'source $PROFILE',
    ]

    setup_env = [
        'echo \'export PATH=$HOME/.local/bin:$PATH\' >> $PROFILE',
        'echo \'export npm_config_userconfig=$HOME/.config/npmrc\' >> $PROFILE',
        'source $PROFILE',
        'mkdir $PREFIX || true',
        'mkdir $SRC || true'
    ]

    run(' && '.join(common + setup_env), shell=True)

    install_node_and_npm = [
        'cd $SRC',
        ('curl -z node-latest.tar.gz'
         ' -O http://nodejs.org/dist/node-latest.tar.gz'),
        'tar xz --strip-components=1 --file node-latest.tar.gz',
        './configure --prefix=$PREFIX',
        'make install',
        'curl -L https://www.npmjs.org/install.sh | sh'
    ]

    run(' && '.join(common + install_node_and_npm), shell=True)


def install_deb():
    with sudo():
        lbs_release = debian.lbs_release()

        # 12.04 ships with really old nodejs, TODO: 14.04?
        if lbs_release in ['10.04', '12.04']:
            info('Adding ppa...')
            debian.add_apt_ppa('chris-lea/node.js', src=True)

        info('Installing Node.js')
        debian.apt_get('install', 'nodejs')

        if lbs_release == '14.04':
            info('Installing NPM')
            debian.apt_get('install', 'npm')
            debian.ln('/usr/bin/nodejs', '/usr/bin/node')


def install_packages():
    packages = blueprint.get('packages', [])
    if packages:
        info('Installing Packages')
        npm('install', *packages)


def npm(command, *options):
    info('Running npm {}', command)
    with sudo():
        run('npm {} -g {}'.format(command, ' '.join(options)))
