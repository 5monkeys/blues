"""
MailDev Blueprint
=================

**Fabric environment:**

.. code-block:: yaml

    blueprints:
      - blues.maildev

    settings:
      maildev:
         web_port: 5000 # default: 5200
         smtp_port: 1025 # default: 5201
         ip: 0.0.0.0 # default: 127.0.0.1

"""
from fabric.decorators import task
from fabric.utils import abort
from refabric.api import run
from refabric.context_managers import sudo
from refabric.contrib import blueprints

from . import debian, node, user

__all__ = ['start', 'stop', 'restart', 'setup', 'configure']


blueprint = blueprints.get(__name__)

start = debian.service_task('maildev', 'start')
stop = debian.service_task('maildev', 'stop')
restart = debian.service_task('maildev', 'restart')


@task
def setup():
    """
    Install maildev
    """
    install()
    configure()


def install():
    # Ensure Node is installed
    node.install()

    # Create maildev user and group
    install_user()

    # Install maildev
    install_maildev()


def install_user():
    with sudo():
        user.create_service_user('maildev')


def install_maildev():
    node.npm('install', 'maildev')


@task
def configure():
    """
    Configure maildev
    """
    if debian.lsb_release() < '16.04':
        abort("This blueprint requires Ubuntu 16.04+.")
        return

    context = {
        'web_port': blueprint.get('web_port', 5200),
        'smtp_port': blueprint.get('smtp_port', 5201),
        'ip': blueprint.get('ip', '127.0.0.1'),
        'ipv4_addresses': debian.get_ipv4_addresses(),
    }
    updated_env = blueprint.upload(
        './default', '/etc/default/maildev', context
    )
    updated_init = blueprint.upload('system/', '/etc/systemd/system/')
    if updated_init:
        run('systemctl daemon-reload', use_sudo=True)

    if any([updated_env, updated_init]):
        restart()
