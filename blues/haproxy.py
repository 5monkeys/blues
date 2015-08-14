from fabric.decorators import task

from refabric.contrib import blueprints

from . import debian

__all__ = ['start', 'stop', 'restart', 'status', 'setup', 'configure']


blueprint = blueprints.get(__name__)

start = debian.service_task('haproxy', 'start')
stop = debian.service_task('haproxy', 'stop')
reload = debian.service_task('haproxy', 'reload')
restart = debian.service_task('haproxy', 'restart')
status = debian.service_task('haproxy', 'status')


@task
def setup():
    """
    Install and configure HAProxy
    """
    install()
    configure()


@task
def install():
    from refabric.context_managers import sudo
    from .debian import add_apt_ppa, apt_get

    with sudo():
        add_apt_ppa('vbernat/haproxy-1.5', src=True)
        apt_get('install', 'haproxy')


@task
def configure():
    """
    Render and upload haproxy.cfg
    """
    uploads = blueprint.upload('./', '/etc/haproxy/')
    if uploads:
        restart()
