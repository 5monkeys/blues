import os
from fabric.contrib import files
from fabric.decorators import task
from refabric.contrib import debian
from refabric.operations import run
from refabric.utils import info


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


def pip(command, virtualenv=None, *options):
    info('Running pip {}', command)
    pip_bin = 'pip'
    if virtualenv:
        pip_bin = os.path.join(virtualenv, 'bin', 'pip')
    run('{} {} {}'.format(pip_bin, command, ' '.join(options)))


def get_virtualenv_path(path, directory='env'):
    return os.path.join(path, directory)
