# coding=utf-8
"""
Neo4j Blueprint
===============

**Fabric environment:**

.. code-block:: yaml

    blueprints:
      - blues.neo4j

    settings:
      neo4j:
        # bind: 0.0.0.0  # Set the bind address specifically (Default: 0.0.0.0)
        # heap_size_mb: 512  # Set the heap size explicitly (Default: auto)

"""
from fabric.decorators import task

from refabric.api import info
from refabric.context_managers import sudo
from refabric.contrib import blueprints

from . import debian

__all__ = ['start', 'stop', 'restart', 'status', 'setup', 'configure']


blueprint = blueprints.get(__name__)

service_name = 'neo4j-service'
start = debian.service_task(service_name, 'start')
stop = debian.service_task(service_name, 'stop')
restart = debian.service_task(service_name, 'restart')
status = debian.service_task(service_name, 'status')


@task
def setup():
    """
    Install and configure Neo4j
    """
    install()
    configure()


def install():
    """
    Install Neo4j
    """
    with sudo():
        from blues import java
        java.install()

        version = blueprint.get('version', '2.2')
        info('Adding apt repository for {} version {}', 'neo4j', version)

        repository = 'http://debian.neo4j.org/repo stable/'.format(version)
        debian.add_apt_repository(repository)

        info('Adding apt key for', repository)
        debian.add_apt_key('http://debian.neo4j.org/neotechnology.gpg.key')
        debian.apt_get_update()

        debian.apt_get('install', 'neo4j')


@task
def configure():
    """
    Configure Neo4j
    """
    context = {
        'bind': blueprint.get('bind', '0.0.0.0'),
        'heap_size_mb': blueprint.get('heap_size_mb', 'auto'),
    }

    updated = False
    for f in [
        'logging.properties',
        'neo4j.properties',
        'neo4j-server.properties',
        'neo4j-wrapper.properties',
    ]:
        updated = bool(blueprint.upload(f, '/etc/neo4j/', context)) or updated

    if updated:
        restart()
