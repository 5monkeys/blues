from fabric.decorators import task

from refabric.api import run, info
from refabric.context_managers import sudo

from . import debian


@task
def setup():
    install()


@task
def upgrade():
    raise NotImplementedError


def install():
    with sudo():
        debian.apt_get('install', 'python-dev', 'python-setuptools')
        run('easy_install -0 pip')


def pip(command, *options):
    info('Running pip {}', command)
    run('pip {} {}'.format(command, ' '.join(options)))
