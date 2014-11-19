from fabric.decorators import task

from refabric.api import run, info
from refabric.context_managers import sudo, silent
from refabric.contrib import blueprints

from . import debian


blueprint = blueprints.get(__name__)

start = debian.service_task('memcached', 'start')
stop = debian.service_task('memcached', 'stop')
restart = debian.service_task('memcached', 'restart')
status = debian.service_task('memcached', 'status')


@task
def setup():
    install()
    upgrade()


def install():
    with sudo():
        debian.apt_get('install', 'memcached')


@task
def upgrade():
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
