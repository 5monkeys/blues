"""
Filebeat Blueprint
==================

**Fabric environment:**

.. code-block:: yaml

    blueprints:
      - blues.filebeat

    settings:
      elasticsearch:
        version: 5.x                       # Version of elastic apt repo to add
        prospector:
          path: /var/log/*.log
          keys_under_root: "false"
          overwrite_keys: "false"
        elasticsearch:
          host: localhost:9200

"""
from fabric.decorators import task
from fabric.utils import abort

from refabric.api import info
from refabric.context_managers import sudo
from refabric.contrib import blueprints

from . import debian
from refabric.operations import run

__all__ = ['start', 'stop', 'restart', 'reload', 'setup', 'configure']


blueprint = blueprints.get(__name__)

start = debian.service_task('filebeat', 'start')
stop = debian.service_task('filebeat', 'stop')
restart = debian.service_task('filebeat', 'restart')
reload = debian.service_task('filebeat', 'force-reload')


@task
def setup():
    """
    Install Filebeat
    """
    install()
    configure()


def install():
    with sudo():
        version = blueprint.get('version', '5.x')
        repository = 'https://artifacts.elastic.co/packages/{0}/apt stable main'.format(version)

        info('Adding apt key for', repository)
        debian.add_apt_key('https://artifacts.elastic.co/GPG-KEY-elasticsearch')

        info('Adding apt repository for {} version {}', 'filebeat', version)
        debian.add_apt_repository(repository)
        debian.apt_get_update()

        # Install
        info('Installing {} version {}', 'filebeat', version)
        debian.apt_get('install', 'filebeat')

        # Enable on boot
        debian.add_rc_service('filebeat', priorities='defaults 95 10')


@task
def configure():
    """
    Configure Filebeat
    """
    context = {
        'prospector': {
            'path': blueprint.get('prospector.path', '/var/log/*.log'),
            'keys_under_root': blueprint.get(
                'prospector.keys_under_root',
                'false'
            ),
            'overwrite_keys': blueprint.get(
                'prospector.overwrite_keys',
                'false'
            )
        },
        'elasticsearch': {
            'host': blueprint.get('elasticsearch.host', 'localhost:9200')
        },
    }
    configured = blueprint.upload('./filebeat.yml', '/etc/filebeat/', context)

    if configured:
        restart()
