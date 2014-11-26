import os

from fabric.decorators import task

from refabric.context_managers import sudo, silent
from refabric.contrib import blueprints
from refabric.operations import run
from refabric.utils import info

__all__ = ['configure']


blueprint = blueprints.get(__name__)


@task
def configure():
    """
    Install crontab per termplate (user)
    """
    with sudo(), silent():
        temp_dir = run('mktemp -d').stdout + os.path.sep
        try:
            updates = blueprint.upload('./', temp_dir)
            run('chmod -R a+rx %s' % temp_dir)

            for update in updates:
                user = os.path.basename(update)
                info('Installing new crontab for {}...', user)
                run('crontab -u {} {}'.format(user, os.path.join(temp_dir, user)))
        finally:
            run('rm -rf {}'.format(temp_dir))
