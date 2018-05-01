"""
Redis Blueprint
===============

**Fabric environment:**

.. code-block:: yaml

    blueprints:
      - blues.redis

    settings:
      redis:
        # bind: 0.0.0.0  # Set the bind address specifically (Default: 127.0.0.1)

"""
import re
from fabric.decorators import task
from fabric.utils import abort

from refabric.context_managers import sudo
from refabric.contrib import blueprints

from . import debian
from refabric.operations import run

__all__ = ['start', 'stop', 'restart', 'setup', 'configure']


blueprint = blueprints.get(__name__)

start = debian.service_task('redis-server', 'start')
stop = debian.service_task('redis-server', 'stop')
restart = debian.service_task('redis-server', 'restart')


@task
def setup():
    """
    Install and configure Redis
    """
    install()
    configure()


def install():
    with sudo():
        debian.apt_get('install', 'redis-server')


def get_installed_version():
    """
    Get installed version as tuple.

    Parsed output format:
    Redis server v=2.8.4 sha=00000000:0 malloc=jemalloc-3.4.1 bits=64 build=a...
    """
    retval = run('redis-server --version')
    m = re.match('.+v=(?P<version>[0-9\.]+).+', retval.stdout)
    try:
        _v = m.group('version')
        v = tuple(map(int, str(_v).split('.')))
        return v
    except IndexError:
        abort('Failed to get installed redis version')


@task
def configure():
    """
    Configure Redis
    """
    context = {
        'bind': blueprint.get('bind', '127.0.0.1')
    }

    version = get_installed_version()

    if version <= (2, 4):
        config = 'redis-2.4.conf'
    elif version < (3, 0):
        config = 'redis-2.8.conf'
    else:
        config = 'redis-3.conf'

    uploads = blueprint.upload(config, '/etc/redis/redis.conf', context)

    if uploads:
        if debian.lbs_release() >= '16.04':
            debian.chown(location='/etc/redis/redis.conf',
                         owner='redis', group='root')
        restart()
