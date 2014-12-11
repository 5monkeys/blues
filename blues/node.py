"""
Node.js Blueprint
=================

**Fabric environment:**

.. code-block:: yaml

    blueprints:
      - blues.node

    settings:
      node:
        packages:            # List of npm packages to install (Optional)
          # - coffee-script

"""
from fabric.decorators import task

from refabric.api import run, info
from refabric.context_managers import sudo
from refabric.contrib import blueprints

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


def install():
    with sudo():
        lbs_release = debian.lbs_release()

        if lbs_release in ['10.04', '12.04']:  # 12.04 ships with really old nodejs, TODO: 14.04?
            info('Adding ppa...')
            debian.add_apt_ppa('chris-lea/node.js', src=True)

        info('Installing Node.js')
        debian.apt_get('install', 'nodejs')

        if lbs_release == '14.04':
            info('Installing NPM')
            debian.apt_get('install', 'npm')
            debian.ln('/usr/bin/nodejs', '/usr/bin/node')


def install_packages():
    info('Installing Packages')
    packages = blueprint.get('packages', [])
    npm('install', *packages)


def npm(command, *options):
    info('Running npm {}', command)
    with sudo():
        run('npm {} -g {}'.format(command, ' '.join(options)))
