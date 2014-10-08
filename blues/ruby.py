from fabric.decorators import task

from refabric.api import run, info
from refabric.context_managers import sudo
from refabric.contrib import blueprints, debian

blueprint = blueprints.get(__name__)


@task
def setup():
    install()


@task
def upgrade():
    install_gems()


def install():
    with sudo():
        info('Installing Ruby v1.9.3')
        debian.apt_get('install', 'ruby1.9.3')

    info('Installing Bundler')
    gem('install', 'bundler')

    install_gems()


def install_gems():
    info('Installing Gems')
    gems = blueprint.get('gems', [])
    gem('install', *gems)


def gem(command, *options):
    info('Running gem {}', command)
    with sudo():
        run('gem {} {} --no-ri --no-rdoc'.format(command, ' '.join(options)))
