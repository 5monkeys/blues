from functools import partial

from fabric.contrib import files
from fabric.decorators import task

from refabric.api import info
from refabric.context_managers import sudo
from refabric.contrib import blueprints, debian

blueprint = blueprints.get(__name__)

start = task(partial(debian.service, 'elasticsearch', 'start', check_status=False))
stop = task(partial(debian.service, 'elasticsearch', 'stop', check_status=False))
restart = task(partial(debian.service, 'elasticsearch', 'restart', check_status=False))
reload = task(partial(debian.service, 'elasticsearch', 'force-reload', check_status=False))


@task
def setup():
    install()
    upgrade()


def install():
    with sudo():
        debian.add_apt_ppa('webupd8team/java')
        debian.debconf_set_selections('shared/accepted-oracle-license-v1-1 select true',
                                      'shared/accepted-oracle-license-v1-1 seen true')
        # Install elastic search
        version = blueprint.get('version', '1.0')
        repository = 'deb http://packages.elasticsearch.org/elasticsearch/{0}/debian stable main'.format(version)
        info('Adding key for {0}'.format(repository))
        debian.add_apt_key('http://packages.elasticsearch.org/GPG-KEY-elasticsearch')
        files.append('/etc/apt/sources.list', repository, shell=True)
        debian.apt_get('update')
        debian.apt_get('install', 'oracle-java7-installer', 'elasticsearch')

        # Enable on boot
        debian.add_rc_service('elasticsearch', priorities='defaults 95 10')


@task
def upgrade():
    context = {
        'cluster_name': blueprint.get('cluster_name', 'elasticsearch'),
        'number_of_shards': blueprint.get('number_of_shards', '5'),
        'number_of_replicas': blueprint.get('number_of_replicas', '0')
    }
    uploads = blueprint.upload('./', '/etc/elasticsearch/', context)
    if uploads:
        restart()
