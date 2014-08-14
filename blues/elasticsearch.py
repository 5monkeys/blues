from fabric.contrib import files
from fabric.decorators import task

from refabric.api import info
from refabric.context_managers import sudo
from refabric.contrib import blueprints, debian

blueprint = blueprints.get(__name__)


@task
def setup():
    install()


def install():
    with sudo():
        debian.add_apt_ppa('webupd8team/java')
        debian.debconf_set_selections('shared/accepted-oracle-license-v1-1 select true',
                                      'shared/accepted-oracle-license-v1-1 seen true')
        # Install elastic search
        repository = 'deb http://packages.elasticsearch.org/elasticsearch/1.0/debian stable main'
        info('Adding key for {0}'.format(repository))
        debian.add_apt_key('http://packages.elasticsearch.org/GPG-KEY-elasticsearch')
        files.append('/etc/apt/sources.list', repository, shell=True)
        debian.apt_get('update')
        debian.apt_get('install', 'oracle-java7-installer', 'elasticsearch')


@task
def upgrade():
    raise NotImplementedError
