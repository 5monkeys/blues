from fabric.decorators import task
from refabric.contrib import debian, blueprints

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
