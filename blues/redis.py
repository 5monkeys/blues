from fabric.decorators import task

from refabric.context_managers import sudo
from refabric.contrib import blueprints

from . import debian

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


@task
def configure():
    """
    Configure Redis
    """
    context = {
        'bind': blueprint.get('bind', '127.0.0.1')
    }
    uploads = blueprint.upload('redis', '/etc/redis/', context)
    if uploads:
        restart()
