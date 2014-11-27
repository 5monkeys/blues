"""
Ruby Blueprint

blueprints:
  - blues.ruby

settings:
  ruby:
    gems:     # List of ruby gems to install (Optional)
      - sass

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
    Install Ruby and configured gems
    """
    install()
    configure()


@task
def configure():
    """
    Install configured gems
    """
    install_gems()


def install():
    with sudo():
        info('Installing Ruby v1.9.3')
        debian.apt_get('install', 'ruby1.9.3')

    info('Installing Bundler')
    gem('install', 'bundler')


def install_gems():
    info('Installing Gems')
    gems = blueprint.get('gems', [])
    gem('install', *gems)


def gem(command, *options):
    info('Running gem {}', command)
    with sudo():
        run('gem {} {} --no-ri --no-rdoc'.format(command, ' '.join(options)))
