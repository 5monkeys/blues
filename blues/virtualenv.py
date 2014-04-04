from contextlib import contextmanager
from fabric.context_managers import prefix
from fabric.contrib import files
from fabric.decorators import task
from refabric.contrib import debian, blueprints
from refabric.operations import run
from refabric.utils import info

blueprint = blueprints.get(__name__)


@task
def setup():
    install()
    upgrade()


def install():
    debian.apt_get('install', 'python-virtualenv')


@task
def upgrade():
    raise NotImplementedError


def create(path):
    if not files.exists(path):
        info('Creating virtualenv: {}', path)
        run('virtualenv {}'.format(path))
    else:
        info('Virtualenv already exists: {}', path)


def pip(command, *options):
    info('Running pip {}', command)
    run('pip {} {}'.format(command, ' '.join(options)))


@contextmanager
def activate(path=None):
    if not path:
        path = debian.pwd()

    with prefix('source %s/bin/activate' % path):
        yield
