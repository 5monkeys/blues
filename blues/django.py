"""
Django Blueprint
================

Management helper blueprint.

**Fabric environment:**

.. code-block:: yaml

    blueprints:
      - blues.django

"""
from fabric.context_managers import cd
from fabric.decorators import task, runs_once
from fabric.operations import prompt
from fabric.state import env

from refabric.api import run, info
from refabric.context_managers import hide_prefix
from refabric.contrib import blueprints

from . import virtualenv
from .application.project import virtualenv_path, python_path, sudo_project

__all__ = ['manage', 'deploy', 'version', 'migrate', 'collectstatic', 'syncdb']


blueprint = blueprints.get(__name__)


@task
def manage(cmd=''):
    """
    Run django management command
    """
    if not cmd:
        cmd = prompt('Enter django management command:')
    with sudo_project(), cd(python_path()), virtualenv.activate(virtualenv_path()), hide_prefix():
        return run('python manage.py {cmd}'.format(cmd=cmd))


@task
def deploy():
    """
    Migrate database and collect static files
    """
    # Migrate database
    migrate()

    # Collect static files
    collectstatic()


@task
def version():
    """
    Get installed version
    """
    if not hasattr(version, 'version'):
        v = manage('--version')
        version.version = tuple(map(int, v.split('\n')[0].strip().split('.')))
    return version.version


@task
@runs_once
def migrate():
    """
    Migrate database
    """
    info('Migrate database')

    options = env.get('django__migrate', '')

    if version() >= (1, 7):
        manage('migrate ' + options)
    elif blueprint.get('use_south', True):
        manage('migrate --merge ' + options)  # TODO: Remove --merge?
        manage('syncdb --noinput')  # TODO: Remove?
    else:
        manage('syncdb --noinput')


@task
@runs_once
def collectstatic():
    """
    Collect static files
    """
    info('Collect static files')
    manage('collectstatic --noinput')


@task
@runs_once
def syncdb():
    """
    Runs manage.py syncdb
    """
    info('Collect static files')
    manage('syncdb')
