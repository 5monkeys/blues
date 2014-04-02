from fabric.decorators import task
from refabric.context_managers import sudo
from refabric.contrib import debian


@task
def install():
    with sudo():
        debian.mkdir('/etc/uwsgi/apps-available')
        debian.mkdir('/etc/uwsgi/apps-enabled')

