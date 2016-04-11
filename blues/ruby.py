"""
Ruby Blueprint
==============

**Fabric environment:**

.. code-block:: yaml

    blueprints:
      - blues.ruby

    settings:
      ruby:
        gems:       # List of ruby gems to install (Optional)
          # - sass

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
    install_gem('bundler')


def install_gems():
    """
    Example with 4 kinds of installs supported (at the same time but on
    different rows),
    * no arguments,
    * multiple gems without arguments,
    * a gem with an argument,
    * a gem with multiple arguments

    gems:
        gem2
        gem4 gem5 gem6
        gem3 -arg3s
        gem1 -arg1 -arg2
    """
    gems = blueprint.get('gems', [])
    if gems:
        info('Installing Gems')
    # for older versions of gem, you can't install on a single row while
    # specifying version so we need to loop the install command accordingly.
    for gem in gems:
        install_gem(gem)


def install_gem(*options):
    info('Running gem install')
    with sudo():
        run('gem install {} --no-ri --no-rdoc'.format(' '.join(options)))
