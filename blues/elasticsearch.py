"""
Elasticsearch Blueprint
=======================

**Fabric environment:**

.. code-block:: yaml

    blueprints:
      - blues.elasticsearch

    settings:
      elasticsearch:
        version: 1.5                       # Version of elasticsearch to install (Required)
        cluster_name: foobar               # Name of the cluster (Default: elasticsearch)
        # heap_size: 1g                    # Heap Size (defaults to 256m min, 1g max)
        # number_of_shards: 1              # Number of shards/splits of an index (Default: 5)
        # number_of_replicas: 0            # Number of replicas / additional copies of an index (Default: 0)
        # network_bind_host: 127.0.0.1     # Set the bind address specifically, IPv4 or IPv6 (Default: 0.0.0.0)
        # network_publish_host: 127.0.0.1  # Set the address other nodes will use to communicate with this node (Optional)
        # network_host: 127.0.0.1          # Set both `network_bind_host` and `network_publish_host` (Optional)
        # queue_size: 3000                 # Set thread pool queue size (Default: 1000)
        # plugins:                         # Optional list of plugins to install
        #   - mobz/elasticsearch-head

"""
from fabric.decorators import task
from fabric.utils import abort

from refabric.api import info
from refabric.context_managers import sudo
from refabric.contrib import blueprints

from . import debian
from refabric.operations import run

__all__ = ['start', 'stop', 'restart', 'reload', 'setup', 'configure',
           'install_plugin']


blueprint = blueprints.get(__name__)

start = debian.service_task('elasticsearch', 'start')
stop = debian.service_task('elasticsearch', 'stop')
restart = debian.service_task('elasticsearch', 'restart')
reload = debian.service_task('elasticsearch', 'force-reload')


@task
def setup():
    """
    Install Elasticsearch
    """
    install()
    configure()


def install():
    with sudo():
        from blues import java
        java.install()

        version = blueprint.get('version', '1.0')
        info('Adding apt repository for {} version {}', 'elasticsearch', version)
        repository = 'http://packages.elasticsearch.org/elasticsearch/{0}/debian stable main'.format(version)
        debian.add_apt_repository(repository)

        info('Adding apt key for', repository)
        debian.add_apt_key('http://packages.elasticsearch.org/GPG-KEY-elasticsearch')
        debian.apt_get('update')

        # Install elasticsearch (and java)
        info('Installing {} version {}', 'elasticsearch', version)
        debian.apt_get('install', 'elasticsearch')

        # Install plugins
        plugins = blueprint.get('plugins', [])
        for plugin in plugins:
            info('Installing elasticsearch "{}" plugin...', plugin)
            install_plugin(plugin)

        # Enable on boot
        debian.add_rc_service('elasticsearch', priorities='defaults 95 10')


@task
def configure():
    """
    Configure Elasticsearch
    """
    context = {
        'cluster_name': blueprint.get('cluster_name', 'elasticsearch'),
        'number_of_shards': blueprint.get('number_of_shards', '5'),
        'number_of_replicas': blueprint.get('number_of_replicas', '0'),
        'bind_host': blueprint.get('network_bind_host'),
        'publish_host': blueprint.get('network_publish_host'),
        'host': blueprint.get('network_host'),
        'queue_size': blueprint.get('queue_size', 1000),
    }
    config = blueprint.upload('./elasticsearch.yml', '/etc/elasticsearch/', context)

    context = {
        'log_level': blueprint.get('log_level', 'WARN'),
    }
    logging = blueprint.upload('./logging.yml', '/etc/elasticsearch/', context)

    context = {
        'heap_size': blueprint.get('heap_size', '256m')
    }
    default = blueprint.upload('./default', '/etc/default/elasticsearch', context)

    if config or logging or default:
        restart()


@task
def install_plugin(name=None):
    if not name:
        abort('No plugin name given')

    with sudo():
        run('/usr/share/elasticsearch/bin/plugin -install {}'.format(name))
