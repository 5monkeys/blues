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
    Example with 6 kinds of installs supported (at the same time but on
    different rows),
    * no arguments,
    * multiple gems without arguments,
    * a gem with an argument,
    * a gem with multiple arguments
    * old style specified version
    * new style specified version

    gems:
        gem2
        gem4 gem5 gem6
        gem3 -arg3s
        gem1 -arg1 -arg2
        gem5 -v 1.0
        gem6:1.0
    """
    gems = blueprint.get('gems', [])
    if gems:
        info('Installing Gems')
        # For older versions of gem (1.9-), you can't install on a single row
        # while specifying version so we need to loop the install command
        # accordingly.
        non_legacy_gems = []
        for gem in gems:
            if '-v' in gem or '--version' in gem:
                install_gem(gem)
            else:
                non_legacy_gems.append(gem)

        # For newer versions of gems we can optimize the install call to a
        # single call, for what it's worth.
        if non_legacy_gems:
            install_gem(*non_legacy_gems)


def install_gem(*options):
    info('Running gem install')
    with sudo():
        run('gem install {} --no-ri --no-rdoc'.format(' '.join(options)))
