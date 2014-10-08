from contextlib import contextmanager

from fabric.context_managers import prefix
from fabric.contrib import files
from fabric.decorators import task

from refabric.api import run, info
from refabric.contrib import blueprints, debian

blueprint = blueprints.get(__name__)


@task
def setup():
    install()


@task
def upgrade():
    raise NotImplementedError


def install():
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
