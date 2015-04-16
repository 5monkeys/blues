"""
Wowza Blueprint
===============

**Fabric environment:**

.. code-block:: yaml

    blueprints:
      - blues.wowza

"""
from fabric.decorators import task

from refabric.api import run, info
from refabric.context_managers import sudo
from refabric.contrib import blueprints

from . import debian

__all__ = ['start', 'stop', 'restart', 'setup', 'configure']


blueprint = blueprints.get(__name__)

start = debian.service_task('WowzaStreamingEngine', 'start')
stop = debian.service_task('WowzaStreamingEngine', 'stop')
restart = debian.service_task('WowzaStreamingEngine', 'restart')

wowza_root ='/usr/local/WowzaMediaServer/'

@task
def setup():
    """
    Install and configure Wowza
    """
    install()
    configure()


def install():
    with sudo():

        info('Downloading wowza')
        version = blueprint.get('wowza_version', '4.1.2')
        binary = 'WowzaStreamingEngine-{}.deb.bin'.format(version)
        version_path = version.replace('.', '-')
        url = 'http://www.wowza.com/downloads/WowzaStreamingEngine-{}/{}'.format(version_path,
                                                                                 binary)
        run('wget -P /tmp/ {url}'.format(url=url))

        debian.chmod('/tmp/{}'.format(binary), '+x')
        info('Installing wowza')
        run('/tmp/{}'.format(binary))


@task
def configure():
    """
    Configure Wowza
    """
