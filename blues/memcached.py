from functools import partial

from fabric.decorators import task

from refabric.api import run, info
from refabric.context_managers import sudo, silent
from refabric.contrib import blueprints, debian

blueprint = blueprints.get(__name__)

start = task(partial(debian.service, 'memcached', 'start', check_status=False))
stop = task(partial(debian.service, 'memcached', 'stop', check_status=False))
restart = task(partial(debian.service, 'memcached', 'restart', check_status=False))
status = task(partial(debian.service, 'memcached', 'status', check_status=False))


@task
def setup():
    debian.apt_get('install', 'memcached')


def install():
    debian.apt_get('install', 'memcached')


@task
def upgrade():
    context = {
        'size': blueprint.get('size', 256),
        'bind': blueprint.get('bind', '127.0.0.1')
    }
    blueprint.upload('memcached', '/etc/', context)


@task
def flush():
    info('Flushing Memcached...')
    with sudo(), silent():
        run('echo "flush_all" | /bin/netcat -q 2 127.0.0.1 11211')
    info('Down the drain!')
