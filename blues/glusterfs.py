from fabric.decorators import task

from refabric.contrib import blueprints

__all__ = ['setup']


blueprint = blueprints.get(__name__)


@task
def setup():
    """
    Install glusterfs-client
    """
    install()


@task
def install():
    from refabric.context_managers import sudo
    from .debian import add_apt_ppa, apt_get

    with sudo():
        apt_get('install', 'software-properties-common')
        add_apt_ppa('gluster/glusterfs-3.5', src=True)
        apt_get('install', 'glusterfs-client')
