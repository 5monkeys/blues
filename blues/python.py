"""
Python Blueprint
================

Does not install python itself, only develop and setup tools.
Contains pip helper for other blueprints to use.

**Fabric environment:**

.. code-block:: yaml

    blueprints:
      - blues.python

"""
from fabric.decorators import task

from refabric.api import run, info
from refabric.context_managers import sudo

from . import debian

__all__ = ['setup']


pip_log_file = '/tmp/pip.log'


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
        run('easy_install pip')
        run('touch {}'.format(pip_log_file))
        debian.chmod(pip_log_file, mode=777)
        pip('install', 'setuptools', '--upgrade')

def pip(command, *options):
    info('Running pip {}', command)
    run('pip {0} {1} -v --log={2} --log-file={2}'.format(command, ' '.join(options), pip_log_file))
