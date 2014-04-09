from fabric.decorators import task
from refabric.contrib import debian


@task
def setup():
    install()


def install():
    debian.apt_get('install', 'redis')
