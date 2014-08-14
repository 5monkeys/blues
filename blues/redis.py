from functools import partial

from fabric.decorators import task

from refabric.context_managers import sudo
from refabric.contrib import debian, blueprints

blueprint = blueprints.get(__name__)

start = task(partial(debian.service, 'redis-server', 'start', check_status=False))
stop = task(partial(debian.service, 'redis-server', 'stop', check_status=False))
restart = task(partial(debian.service, 'redis-server', 'restart', check_status=False))


@task
def setup():
    install()


def install():
    with sudo():
        debian.apt_get('install', 'redis-server')


@task
def upgrade():
    context = {
        'bind': blueprint.get('bind', '127.0.0.1')
    }
    uploads = blueprint.upload('redis', '/etc/redis/', context)
    if uploads:
        restart()
