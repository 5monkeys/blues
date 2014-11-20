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
    if not files.exists(path):
        info('Creating virtualenv: {}', path)
        run('virtualenv {}'.format(path))
    else:
        info('Virtualenv already exists: {}', path)


@contextmanager
def activate(path=None):
    if not path:
        path = debian.pwd()

    with prefix('source %s/bin/activate' % path):
        yield
