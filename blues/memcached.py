"""
Memcached Blueprint

blueprints:
  - blues.memcached

settings:
  memcached:
    # size: 256          # Cache size in mb (Default: 64)
    # bind: 127.0.0.1  # Set the bind address specifically (Default: listen to all)

"""
from fabric.decorators import task

from refabric.api import run, info
from refabric.context_managers import sudo, silent
from refabric.contrib import blueprints

from . import debian

__all__ = ['start', 'stop', 'restart', 'status', 'setup', 'configure', 'flush']


blueprint = blueprints.get(__name__)

start = debian.service_task('memcached', 'start')
stop = debian.service_task('memcached', 'stop')
restart = debian.service_task('memcached', 'restart')
status = debian.service_task('memcached', 'status')


@task
def setup():
    """
    Install memcached
    """
    install()
    configure()


def install():
    with sudo():
        debian.apt_get('install', 'memcached')


@task
def configure():
    """
    Configure memcached
    """
    context = {
        'size': blueprint.get('size', 64),
        'bind': blueprint.get('bind', None)
    }
    blueprint.upload('memcached', '/etc/', context)


@task
def flush():
    """
    Delete all cached keys
    """
    info('Flushing Memcached...')
    with sudo(), silent():
        run('echo "flush_all" | /bin/netcat -q 2 127.0.0.1 11211')
    info('Down the drain!')
