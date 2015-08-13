"""
Incron Blueprint
================

This blueprint has no settings.
Templates are handled as crontabs.

**Fabric environment:**

.. code-block:: yaml

    blueprints:
      - blues.incron
"""

from fabric.decorators import task

from refabric.contrib import blueprints

from blues import debian

blueprint = blueprints.get(__name__)

restart = debian.service_task('incron', 'restart')

@task
def setup():
    """
    Install and configure incron
    """
    install()
    configure()


def install():
    """
    Install incron
    """
    from refabric.utils import info

    info('Install {}', 'incron')
    debian.apt_get('install', 'incron')


@task
def configure():
    """
    Install incrontabs
    """
    import os

    from fabric.contrib import files
    from refabric.context_managers import sudo


    with sudo():
        debian.mkdir('/etc/incron.available/', mode=755)
        uploads = blueprint.upload('./', '/etc/incron.available/')
        for tab in uploads:
            src  = os.path.join('/etc/incron.available', tab)
            dest = os.path.join('/etc/incron.d', tab)
            debian.cp(src, dest)

    if uploads:
        restart()
