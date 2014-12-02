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
        info('Installing Node.js')
        if debian.lbs_release() in ['10.04', '12.04']:  # 12.04 ships with really old nodejs, TODO: 14.04?
            debian.add_apt_ppa('chris-lea/node.js', src=True)
        debian.apt_get('install', 'nodejs', 'npm')
        if debian.lbs_release() == '14.04':
            debian.ln('/usr/bin/nodejs', '/usr/bin/node')


def install_packages():
    info('Installing Packages')
    packages = blueprint.get('packages', [])
    npm('install', *packages)


def npm(command, *options):
    info('Running npm {}', command)
    with sudo():
        run('npm {} -g {}'.format(command, ' '.join(options)))
