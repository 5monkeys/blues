"""
PHP
====

Installs PHP with FastCGI support

**Fabric environment:**

.. code-block:: yaml

    blueprints:
      - blues.php

"""
from fabric.decorators import task

from refabric.api import info
from refabric.context_managers import sudo

from . import debian

__all__ = ['setup']


@task
def setup():
    """
    Install PHP
    """
    install()


def install():
    with sudo():
        info('Install PHP with FastCGI support')
        debian.apt_get('install', 'php5-cli', 'php5-fpm')
