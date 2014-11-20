from fabric.decorators import task

from refabric.api import run, info
from refabric.context_managers import sudo

from . import debian

__all__ = ['setup']


@task
def setup():
    """
    Install python develop tools
    """
    install()


def install():
    with sudo():
        info('Install python dependencies')
        debian.apt_get('install', 'python-dev', 'python-setuptools')
        run('easy_install -0 pip')


def pip(command, *options):
    info('Running pip {}', command)
    run('pip {} {} -v --log=/tmp/pip.log --log-file=/tmp/pip.log'.format(command, ' '.join(options)))
