from fabric.context_managers import cd
from fabric.decorators import task, runs_once
from fabric.operations import prompt

from refabric.api import run, info
from refabric.context_managers import shell_env
from refabric.contrib import blueprints

from . import virtualenv
from .application.project import virtualenv_path, python_path, sudo_project


blueprint = blueprints.get(__name__)


@task
def manage(cmd=''):
    if not cmd:
        cmd = prompt('Enter django management command:')
    with sudo_project(), cd(python_path()), virtualenv.activate(virtualenv_path()), shell_env():
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
    if not hasattr(version, 'version'):
        v = manage('--version')
        version.version = tuple(map(int, v.split('\n')[0].strip().split('.')))
    return version.version


@task
@runs_once
def migrate():
    info('Migrate database')
    if version() >= (1, 7):
        manage('migrate')
    elif blueprint.get('use_south', True):
        manage('migrate --merge')
    else:
        manage('syncdb --noinput')


@task
@runs_once
def collectstatic():
    info('Collect static files')
    manage('collectstatic --noinput')
