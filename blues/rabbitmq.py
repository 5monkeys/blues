from functools import partial

from fabric.decorators import task

from refabric.api import run, info
from refabric.context_managers import sudo
from refabric.contrib import blueprints, debian

blueprint = blueprints.get(__name__)

start = task(partial(debian.service, 'rabbitmq-server', 'start', check_status=False))
stop = task(partial(debian.service, 'rabbitmq-server', 'stop', check_status=False))
restart = task(partial(debian.service, 'rabbitmq-server', 'restart', check_status=False))
reload = task(partial(debian.service, 'rabbitmq-server', 'reload', check_status=False))


@task
def setup():
    install()
    upgrade()


def install():
    package_name = 'rabbitmq-server'
    debian.debconf_set_selections('%s rabbitmq-server/upgrade_previous note' % package_name)

    with sudo():
        info('Adding apt key for {}', package_name)
        run("apt-key adv --keyserver pgp.mit.edu --recv-keys 0x056E8E56")

        info('Adding apt repository for {}', package_name)
        debian.add_apt_repository('http://www.rabbitmq.com/debian/ testing main')
        debian.apt_get('update')

        info('Installing {}', package_name)
        debian.apt_get('install', package_name)


@task
def upgrade():
    uploads = blueprint.upload('./', '/etc/rabbitmq/')
    if uploads:
        restart()
