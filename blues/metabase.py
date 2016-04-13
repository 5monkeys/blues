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

__all__ = ['install', 'setup']

blueprint = blueprints.get(__name__)
install_path = blueprint.get('install_path', '/usr/local/lib/metabase')


@task
def setup(**kwargs):
    install(**kwargs)


@task
def install(install_java=True):
    with sudo():
        if install_java:
            from blues import java
            java.install()

        conf = {'version': blueprint.get('version', '0.16.1'),
                'path': install_path}

        info('Downloading Metabase v{version} to {path}', **conf)

        run('mkdir -p {path} && cd {path} && curl -O '
            'http://downloads.metabase.com/v{version}/metabase.jar'.format(
                **conf))
