"""
Fstab Blueprint
===============

This blueprint configures the fstab.

**Fabric environment:**

.. code-block:: yaml

    blueprints:
      - blues.fstab

    settings:
      fstab:
        <mount point>:                                        # The mount point where <filesystem> is mounted to
          filesystem: 1.2.3.4:/srv/www                        # The partition or storage device to be mounted (will not mount if not set)
          # type: nfs                                         # The filesystem type (Default: auto)
          # options: defaults,nobootwait,comment=cloudconfig  # Mount options of the filesystem (Default: rw)
          # dump: 1                                           # Used by the dump utility to decide when to make a backup, 0|1 (Default: 0)
          # pazz: 1                                           # Used by fsck to decide which order filesystems are to be checked 0|1|2 (Default: 0)
          # owner: www-data                                   # Name of mount point owner
          # group: www-data                                   # Name of mount point group

"""
from fabric.decorators import task
from fabric.utils import warn

from refabric.contrib import blueprints

from blues import debian

__all__ = ['configure']


blueprint = blueprints.get(__name__)


@task
def configure():
    for mount_point, config in blueprint.get('', {}).items():
        if 'filesystem' in config:
            debian.mount(mount_point, **config)
        else:
            warn('Mount point {} not configured with filesystem, skipping'.format(mount_point))
