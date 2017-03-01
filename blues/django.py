"""
Django Blueprint
================

Management helper blueprint.

**Fabric environment:**

.. code-block:: yaml

    blueprints:
      - blues.django

    settings:
        # manage: ../manage.py  # Manage module relative to python path; ./src (Default: manage.py)
        # use_south: false      # Enable south migrations, only for Django < 1.7 (Default: true)
        # use_syncdb: true      # Enable syncdb, only for Django < 1.7 (Default: false)

"""
import re

from fabric.context_managers import cd
from fabric.decorators import task, runs_once
from fabric.operations import prompt
from fabric.state import env
from fabric.utils import warn

from refabric.api import run, info
from refabric.context_managers import hide_prefix
from refabric.contrib import blueprints
from refabric.context_managers import silent

from . import virtualenv
from .application.project import virtualenv_path, python_path, sudo_project

__all__ = [
    'manage', 'deploy', 'version', 'migrate',
    'collectstatic', 'count_new_statics', 'syncdb']


blueprint = blueprints.get(__name__)


@task
def manage(cmd=''):
    """
    Run django management command
    """
    if not cmd:
        cmd = prompt('Enter django management command:')
    with sudo_project(), cd(python_path()), virtualenv.activate(virtualenv_path()), hide_prefix():
        return run('python {manage} {cmd}'.format(cmd=cmd, manage=blueprint.get('manage', 'manage.py')))


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
        v = re.split('[a-z]', v.split('\n')[-1])[0]
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
    else:
        if blueprint.get('use_syncdb', False):
            manage('syncdb --noinput')
        if blueprint.get('use_south', True):
            manage('migrate --merge ' + options)  # TODO: Remove --merge?


@task
@runs_once
def collectstatic(dryrun=False):
    """
    Collect static files
    """
    if not dryrun:
        info('Collect static files')

    return manage('collectstatic --noinput{}'.format(
        ' -n' if dryrun else ''
    ))


@task
@runs_once
def count_new_statics():
    """
    Return the number of static files that will be copied with a collectstatic
    or None.
    """
    with silent():
        # NOTE: Don't call `collectstatic(dryrun=True)` here, since that
        # function is marked with `@runs_once`. That would result in users only
        # being able to call _either_ `collectstatic` _or_ `count_new_statics`,
        # but not both.
        output = manage('collectstatic --noinput -n').stdout

        matcher = r'(?P<num>\d+) static files? copied'

        matched = re.search(matcher, output)

        if matched:
            try:
                changed = int(matched.group('num'))
                info(
                    '{{}} static file{} to be copied.'.format(
                        's' if changed > 1 else ''
                    ), changed)
                return changed
            except ValueError:
                pass

        warn("Couldn't determine number of static files to be copied.")


@task
@runs_once
def syncdb():
    """
    Runs manage.py syncdb
    """
    info('Collect static files')
    manage('syncdb')
