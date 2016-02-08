# coding=utf-8
"""
Metabase Blueprint
===============

**Fabric environment:**

.. code-block:: yaml

    blueprints:
      - blues.metabase

    settings:
      metabase:
        version: 0.13.3

"""
from fabric.decorators import task

from refabric.api import info
from refabric.context_managers import sudo
from refabric.contrib import blueprints
from refabric.operations import run

__all__ = [
    'install',
]

blueprint = blueprints.get(__name__)


@task
def setup():
    install()


@task
def install(install_java=True):
    with sudo():
        if install_java:
            from blues import java
            java.install()

        version = blueprint.get('version', '0.13.3')
        info('Downloading Metabase v%s' % version)
        run('mkdir -p /etc/metabase/ && cd /etc/metabase/ && curl -O '
            'http://downloads.metabase.com/v%s/metabase.jar' % version)
