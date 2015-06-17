"""
Memcached Blueprint
===================

**Fabric environment:**

.. code-block:: yaml

    blueprints:
      - blues.varnish

    settings:
      varnish:
        # size: 1024m        # Cache size in mb (Default: 256m)
        # bind: :81  # Set the bind address specifically (Default: :6081)
        # backend: 127.0.0.1:82  # Set the bind address specifically (Default: 127.0.0.1:8080)

"""
from fabric.decorators import task

from refabric.api import run, info
from refabric.context_managers import sudo, silent
from refabric.contrib import blueprints

from . import debian

__all__ = ['start', 'stop', 'restart', 'status', 'setup', 'configure', 'flush']


blueprint = blueprints.get(__name__)

start = debian.service_task('varnish', 'start')
stop = debian.service_task('varnish', 'stop')
restart = debian.service_task('varnish', 'restart')
status = debian.service_task('varnish', 'status')


@task
def setup():
    """
    Install varnish
    """
    install()
    configure()


def install():
    with sudo():
        debian.apt_get('install', 'varnish')


@task
def configure():
    """
    Configure varnish
    """
    context = {
        'size': blueprint.get('size', '256m'),
        'bind': blueprint.get('bind', ':6081'),
        'backend': blueprint.get('backend', '127.0.0.1:8080')
    }
    default = blueprint.upload('./default', '/etc/default/varnish', context)

    if default:
        restart()


@task
def varnishadm(cmd):
    """
    Run varnishadm with argument
    """
    with sudo():
        run("varnishadm '{}'".format(cmd))


@task
def flush():
    """
    Clear varnish cache
    """
    info('Flushing Varnish...')
    varnishadm('ban.url .*')
    info('Down the drain!')
