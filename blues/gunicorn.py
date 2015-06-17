from fabric.decorators import task
from refabric.context_managers import sudo, silent, hide_prefix
from refabric.contrib import blueprints

from . import python

blueprint = blueprints.get(__name__)


@task
def setup():
    install()
    configure()


def install():
    with sudo():
        python.install()


def configure():
    pass