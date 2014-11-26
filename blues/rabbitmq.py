from fabric.decorators import task
from fabric.utils import abort

from refabric.api import run, info
from refabric.context_managers import sudo
from refabric.contrib import blueprints

from . import debian

__all__ = ['start', 'stop', 'restart', 'reload', 'setup', 'configure', 'ctl']


blueprint = blueprints.get(__name__)

start = debian.service_task('rabbitmq-server', 'start')
stop = debian.service_task('rabbitmq-server', 'stop')
restart = debian.service_task('rabbitmq-server', 'restart')
reload = debian.service_task('rabbitmq-server', 'reload')


@task
def setup():
    """
    Install Rabbitmq
    """
    if debian.lbs_release() < '14.04':
        install_testing()
    else:
        install_stable()

    configure()

    enable_plugins('rabbitmq_management')


def install_stable():
    with sudo():
        debian.apt_get('install', 'rabbitmq-server')


def install_testing():
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


def enable_plugins(plugin):
    with sudo():
        info('Enable {} plugin', plugin)
        output = run('rabbitmq-plugins enable {}'.format(plugin))
        if output.stdout.strip().startswith('The following plugins have been'):
            restart()


@task
def configure():
    """
    Configure Rabbitmq
    """
    uploads = blueprint.upload('./', '/etc/rabbitmq/')
    if uploads:
        restart()


@task
def ctl(command=None):
    """
    Run rabbitmqctl with given command
    :param command:
    :return:
    """
    if not command:
        abort('No command given, $ fab rabbitmq.ctl:stop_app')

    with sudo():
        run('rabbitmqctl {}'.format(command))
