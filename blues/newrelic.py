"""
NewRelic Server Blueprint
=================

**Fabric environment:**

.. code-block:: yaml

    blueprints:
      - blues.newrelic

    settings:
      newrelic:
        # newrelic_key: XXXXX

"""
from fabric.decorators import task
from refabric.api import run, info

from refabric.context_managers import sudo
from refabric.contrib import blueprints

from . import debian

__all__ = ['start', 'stop', 'restart', 'setup', 'configure']


blueprint = blueprints.get(__name__)


start = debian.service_task('newrelic-sysmond', 'start')
stop = debian.service_task('newrelic-sysmond', 'stop')
restart = debian.service_task('newrelic-sysmond', 'restart')


@task
def setup():
    """
    Install and configure newrelic server
    """
    install()
    configure()


def install():
    with sudo():
        info('Adding apt repository for Newrelic')
        debian.add_apt_repository(
            'http://apt.newrelic.com/debian/ newrelic non-free')
        info('Adding newrelic apt key')
        debian.add_apt_key('https://download.newrelic.com/548C16BF.gpg')
        debian.apt_get('update')
        info('Installing newrelic-sysmond')
        debian.apt_get('install', 'newrelic-sysmond')


@task
def configure():
    """
    Configure newrelic server
    """

    with sudo():
        info('Adding license key to config')
        newrelic_key = blueprint.get('newrelic_key', None)
        run('nrsysmond-config --set license_key={}'.format(newrelic_key))
