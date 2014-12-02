"""
MongoDB Blueprint
=================

**Fabric environment:**

.. code-block:: yaml

    blueprints:
      - blues.mongodb

    settings:
      mongodb:
        # bind: 0.0.0.0  # Set the bind address specifically (Default: 127.0.0.1)

"""
from fabric.decorators import task

from refabric.context_managers import sudo
from refabric.contrib import blueprints

from . import debian

__all__ = ['start', 'stop', 'restart', 'setup', 'configure']


blueprint = blueprints.get(__name__)

start = debian.service_task('mongodb', 'start')
stop = debian.service_task('mongodb', 'stop')
restart = debian.service_task('mongodb', 'restart')


@task
def setup():
    """
    Install and configure mongodb
    """
    install()
    configure()


def install():
    with sudo():
        debian.apt_get('install', 'mongodb')


@task
def configure():
    """
    Configure mongodb
    """
    context = {
        'bind': blueprint.get('bind', '127.0.0.1')
    }
    uploads = blueprint.upload('mongodb.conf', '/etc/mongodb.conf', context)
    if uploads:
        restart()
