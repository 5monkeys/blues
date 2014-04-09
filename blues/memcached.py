from fabric.decorators import task
from refabric.context_managers import sudo, silent
from refabric.contrib import debian, blueprints
from refabric.operations import run
from refabric.utils import info

blueprint = blueprints.get(__name__)


@task
def setup():
    debian.apt_get('install', 'memcached')


def install():
    debian.apt_get('install', 'memcached')


@task
def upgrade():
    context = {
        'size': blueprint.get('size', 256)
    }
    blueprint.upload('memcached', '/etc/', context)


@task
def flush():
    info('Flushing Memcached...')
    with sudo(), silent():
        run('echo "flush_all" | /bin/netcat -q 2 127.0.0.1 11211')
    info('Down the drain!')
