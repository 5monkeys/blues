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
import json

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
    payload = json.dumps({ 'deployment': {
            'description': new_tag,
            'revision': commit_hash,
            'changelog': changes,
            'user': deployer,
            }
    })
    :param payload: payload is a json dict with newrelic api info
    :return:
    """
    newrelic_key = blueprint.get('newrelic_key', None)
    app_id = blueprint.get('app_id', None)


    if all([newrelic_key, app_id]):
        url = 'https://api.newrelic.com/v2/applications/{}/deployments.json'.format(app_id)
        headers = {
            'x-api-key': newrelic_key,
            'Content-Type': 'application/json'
        }

        if not payload:
            path = python_path()
            commit_hash = git.get_commit(path)
            new_tag, old_tag = git.get_two_most_recent_tags(path)
            changes = git.log_between_tags(path, old_tag, new_tag)
            deployer = git.get_local_commiter()

            payload = json.dumps({ 
                'deployment': {
                    'description': new_tag,
                    'revision': commit_hash,
                    'changelog': changes,
                    'user': deployer,
                }
            })

        request = urllib2.Request(url, headers=headers)
        urllib2.urlopen(request, data=payload)
        info('Deploy event sent')
    else:
        for i in ['app_id', 'newrelic_key']:
             if not locals().get(i, None):
                 info('missing key: {}'.format(i))
