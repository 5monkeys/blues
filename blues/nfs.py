"""
NFS Blueprint
=============

**Fabric environment:**

.. code-block:: yaml

    blueprints:
      - blues.nfs

    settings:
      nfs:
        exports:
          /foo/bar:                                              # Path to export
            host: 10.0.0.0/24                                    # Host mask to allow
            # mode: 755                                          # Optional file mode on exported path
            # owner: foobar                                      # Optional owner of exported path
            # group: foobar                                      # Optional group of exported path
            # options: rw,async,no_root_squash,no_subtree_check  # Optional export options

"""
from fabric.context_managers import cd
from fabric.contrib import files

from fabric.decorators import task

from refabric.context_managers import sudo
from refabric.contrib import blueprints
from refabric.utils import info

from blues import debian

__all__ = ['start', 'stop', 'restart', 'reload', 'setup', 'configure']


blueprint = blueprints.get(__name__)

start = debian.service_task('nfs-kernel-server', 'start')
stop = debian.service_task('nfs-kernel-server', 'stop')
restart = debian.service_task('nfs-kernel-server', 'restart')
reload = debian.service_task('nfs-kernel-server', 'reload')


@task
def setup():
    """
    Install and configure nfs server
    """
    install()
    configure()


def install():
    with sudo():
        debian.apt_get('install', 'nfs-kernel-server')
        start()


@task
def configure():
    """
    Configure nfs server exports table
    """
    export_changes = []
    for path, config in blueprint.get('exports', {}).items():
        with sudo():
            mode = config.get('mode')
            owner = config.get('owner')
            group = config.get('group')
            debian.mkdir(path, mode=mode, owner=owner, group=group)

        if 'host' in config:
            kwargs = {
                'host': config['host']
            }
            if 'options' in config:
                kwargs['options'] = config['options']

            exported = export(path, **kwargs)
            export_changes.append(exported)

    if any(export_changes):
        restart()


def export(path, host, options='rw,async,no_root_squash,no_subtree_check'):
    config_line = '%s\t\t%s(%s)' % (path, host, options)
    with sudo(), cd('/etc'):
        if not files.contains('exports', config_line):
            info('Exporting: {}', path)
            files.append('exports', config_line)
            return True
    return False
