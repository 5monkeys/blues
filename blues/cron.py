"""
Cron Blueprint
==============

This blueprint has no settings.
Templates are handled as crontabs and should be named after related user.

**Fabric environment:**

.. code-block:: yaml

    blueprints:
      - blues.cron

"""
import os

from fabric.decorators import task

from refabric.context_managers import sudo, silent
from refabric.contrib import blueprints
from refabric.operations import run
from refabric.utils import info

from blues import debian

__all__ = ['configure']


blueprint = blueprints.get(__name__)


@task
def configure():
    """
    Install crontab per template (i.e. user)
    """
    with sudo(), silent():
        with debian.temporary_dir(mode=555) as temp_dir:
            updates = blueprint.upload('./', temp_dir)
            for update in updates:
                user = os.path.basename(update)
                info('Installing new crontab for {}...', user)
                run('crontab -u {} {}'.format(user, os.path.join(temp_dir, user)))
