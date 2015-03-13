"""
Virtualenv Blueprint
====================

Installs virtualenv and contains useful virtualenv commands for other blueprints to use.

**Fabric environment:**

.. code-block:: yaml

    blueprints:
      - blues.virtualenv

"""
from contextlib import contextmanager

from fabric.context_managers import prefix
from fabric.contrib import files
from fabric.decorators import task

from refabric.api import run, info
from refabric.context_managers import sudo
from refabric.contrib import blueprints

from . import debian
from . import python

__all__ = ['setup']


blueprint = blueprints.get(__name__)


@task
def setup():
    """
    Install system wide virtualenv binary
    """
    with sudo():
        install()


def install():
    python.install()
    info('Install {}', 'virtualenv')
    debian.apt_get('install', 'python-virtualenv')


def create(path):
    options = ''

    if python.requested_version() > (3,):
        options += ' -p /usr/bin/python3'

    if not files.exists(path):
        info('Creating virtualenv: {}', path)
        run('virtualenv{options} {}'.format(path, options=options))
    else:
        info('Virtualenv already exists: {}', path)


@contextmanager
def activate(path=None):
    if not path:
        path = debian.pwd()

    with prefix('source %s/bin/activate' % path):
        yield
