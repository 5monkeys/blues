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
from .application.project import python_path


from . import debian, git

import urllib2
import urllib

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


def send_deploy_event(payload=None):
    """
    Sends deploy event to newrelic
    payload ={
        'deployment[app_name]': app_name,
        'deployment[description]': new_tag,
        'deployment[revision]': commit_hash,
        'deployment[changelog]': changes,
        'deployment[user]': deployer,
    }
    :param payload: payload is a dict with newrelic api info
    :return:
    """
    newrelic_key = blueprint.get('newrelic_key', None)
    app_name = blueprint.get('app_name', None)

    if newrelic_key and app_name:
        url = 'https://api.newrelic.com/deployments.xml'
        headers = {'x-api-key': newrelic_key}

        if not payload:
            commit_hash = git.get_commit(python_path())
            new_tag, old_tag = git.get_two_most_recent_tags(python_path())
            changes = git.log_between_tags(python_path(), old_tag, new_tag)
            deployer = git.get_local_commiter()

            payload = {
                    'deployment[app_name]': app_name,
                    'deployment[description]': new_tag,
                    'deployment[revision]': commit_hash,
                    'deployment[changelog]': changes,
                    'deployment[user]': deployer,
                }

        request = urllib2.Request(url, headers=headers)
        request_payload = urllib.urlencode(payload)
        urllib2.urlopen(request, data=request_payload)
        info('Deploy event sent')
    else:
        info('No key found')
