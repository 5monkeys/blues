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

from refabric.api import run, info
from refabric.context_managers import sudo, silent
from refabric.contrib import blueprints

from blues import debian

__all__ = ['start', 'stop', 'restart', 'reload', 'setup', 'configure',
           'show_exports']


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


def get_existing_exports():
    with silent('warnings'):
        out = run('cat /etc/exports')
    return [r for r in out.replace('\r', '').split('\n')
            if not r.strip().startswith('#')]


@task
def show_exports():
    info('Showing existing exports:')
    for ex in get_existing_exports():
        info('  ' + ex)


def export(path, host, options='rw,async,no_root_squash,no_subtree_check'):
    config_line = '%s\t\t%s(%s)' % (path, host, options)
    with sudo(), cd('/etc'):
        existing_lines = get_existing_exports()
        if config_line not in existing_lines:
            info('Exporting: {}', path)
            files.append('exports', config_line)
            return True
    return False
