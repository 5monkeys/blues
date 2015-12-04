"""
Incron Blueprint
==============

This blueprint has no settings.
Templates are handled as incrontabs and should be named after related user.

**Fabric environment:**

.. code-block:: yaml

    blueprints:
      - blues.incron

"""

import os
from StringIO import StringIO

from fabric.decorators import task
from fabric.operations import put

from refabric.context_managers import sudo, silent
from refabric.contrib import blueprints
from refabric.operations import run
from refabric.utils import info

from blues import debian

__all__ = ['setup', 'configure']


blueprint = blueprints.get(__name__)


@task
def setup():
    """
    Install and configure incron
    """
    install()
    configure()


def install():
    with sudo():
        debian.apt_get('install', 'incron')


@task
def configure():
    """
    Install incrontab per template (i.e. user)
    """
    with sudo(), silent():
        updates = blueprint.upload('./', '/etc')

        users = [os.path.basename(update) for update in updates]
        put(StringIO('\n'.join(users)), '/etc/incron.allow', use_sudo=True)

        for user in users:
            info('Installing new incrontab for {}...', user)
            run('incrontab -u {} {}'.format(user, os.path.join('/etc/incron.usertables', user)))


