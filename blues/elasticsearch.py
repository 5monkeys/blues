from fabric.decorators import task

from refabric.api import info
from refabric.context_managers import sudo
from refabric.contrib import blueprints

from . import debian


blueprint = blueprints.get(__name__)

start = debian.service_task('elasticsearch', 'start')
stop = debian.service_task('elasticsearch', 'stop')
restart = debian.service_task('elasticsearch', 'restart')
reload = debian.service_task('elasticsearch', 'force-reload')


@task
def setup():
    install()
    upgrade()


def install():
    with sudo():
        debian.add_apt_ppa('webupd8team/java')
        debian.debconf_set_selections('shared/accepted-oracle-license-v1-1 select true',
                                      'shared/accepted-oracle-license-v1-1 seen true')

        version = blueprint.get('version', '1.0')
        info('Adding apt repository for {} version {}', 'elasticsearch', version)
        repository = 'http://packages.elasticsearch.org/elasticsearch/{0}/debian stable main'.format(version)
        debian.add_apt_repository(repository)

        info('Adding apt key for', repository)
        debian.add_apt_key('http://packages.elasticsearch.org/GPG-KEY-elasticsearch')
        debian.apt_get('update')

        # Install elasticsearch (and java)
        info('Installing {} version {}', 'elasticsearch', version)
        debian.apt_get('install', 'oracle-java7-installer', 'elasticsearch')

        # Enable on boot
        debian.add_rc_service('elasticsearch', priorities='defaults 95 10')


@task
def upgrade():
    context = {
        'cluster_name': blueprint.get('cluster_name', 'elasticsearch'),
        'number_of_shards': blueprint.get('number_of_shards', '5'),
        'number_of_replicas': blueprint.get('number_of_replicas', '0'),
        'bind_host': blueprint.get('network_bind_host'),
        'publish_host': blueprint.get('network_publish_host'),
        'host': blueprint.get('network_host')
    }
    uploads = blueprint.upload('./', '/etc/elasticsearch/', context)
    if uploads:
        restart()
