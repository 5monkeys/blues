from fabric.decorators import task

from refabric.api import run, info
from refabric.context_managers import sudo
from refabric.contrib import blueprints

from . import debian


blueprint = blueprints.get(__name__)


@task
def setup():
    install()


@task
def upgrade():
    install_packages()


def install():
    with sudo():
        info('Installing Node.js')
        if debian.lbs_release() in ['10.04', '12.04']:  # 12.04 ships with really old nodejs
            debian.add_apt_ppa('chris-lea/node.js', src=True)
        debian.apt_get('install', 'nodejs')

    install_packages()


def install_packages():
    info('Installing Packages')
    packages = blueprint.get('packages', [])
    npm('install', *packages)


def npm(command, *options):
    info('Running npm {}', command)
    with sudo():
        run('npm {} -g {}'.format(command, ' '.join(options)))
