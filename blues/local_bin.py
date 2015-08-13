"""
local_bin Blueprint
================

This blueprint has no settings.
Templates are handled as executables for /usr/local/bin.

**Fabric environment:**

.. code-block:: yaml

    blueprints:
      - blues.local_bin
"""

from fabric.decorators import task

from refabric.contrib import blueprints


blueprint = blueprints.get(__name__)


@task
def configure():
    """
    Install executables
    """
    from refabric.context_managers import sudo

    from blues import debian

    with sudo():
        uploads = blueprint.upload('./', '/usr/local/bin/')
        for executable in uploads:
            debian.chmod('/usr/local/bin/'+executable, mode=755)
