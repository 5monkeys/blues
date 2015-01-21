"""
Solr Blueprint
==============

**Fabric environment:**

.. code-block:: yaml

    blueprints:
      - blues.solr

    settings:
      solr:
        version: 4.10.2  # Solr version to install (Required)
        # memory: 1024m  # Specify minimum and maximum heap size in mb (Default: 512m)

"""
import os

from fabric.context_managers import cd, settings
from fabric.contrib import files
from fabric.decorators import task, parallel

from refabric.api import info, run
from refabric.context_managers import sudo, silent, hide_prefix
from refabric.contrib import blueprints

from . import user
from . import debian

__all__ = ['start', 'stop', 'restart', 'setup', 'configure', 'tail']


blueprint = blueprints.get(__name__)

start = debian.service_task('solr', 'start')
stop = debian.service_task('solr', 'stop')
restart = debian.service_task('solr', 'restart')

solr_home = '/usr/share/solr'


@task
def setup():
    """
    Install Solr
    """
    install()
    configure()


def install():
    # Ensure Java is installed
    from blues import java
    java.install()

    # Create solr user, group and directories
    install_user()

    # Download and extract solr
    install_solr()


def install_user():
    with sudo():
        user.create_service_user('solr', home=solr_home)
        # Home dir will be created by solr installation (symbolic link)

        debian.mkdir('/var/lib/solr', mode=755, owner='solr', group='solr')
        debian.mkdir('/var/log/solr', mode=755, owner='solr', group='solr')


def install_solr():
    with sudo():
        version = blueprint.get('version')
        version_tuple = tuple(map(int, version.split('.')))

        archive = 'solr-{}.tgz'.format(version)
        if version_tuple < (4, 1, 0):
            archive = 'apache-{}'.format(archive)
        url = 'https://archive.apache.org/dist/lucene/solr/{}/{}'.format(version, archive)

        with cd('/tmp'):
            info('Download {} ({})', 'Solr', version)
            run('wget {}'.format(url))

            info('Extracting archive...')
            with silent():
                run('tar xzf {}'.format(archive))
                solr_version_dir = os.path.splitext(archive)[0]
                solr_version_path = os.path.join('/usr', 'share', solr_version_dir)
                debian.chmod(solr_version_dir, 755, 'solr', 'solr', recursive=True)
                if files.exists(solr_version_path):
                    info('Found same existing version, removing it...')
                    debian.rm(solr_version_path, recursive=True)
                debian.mv(solr_version_dir, '/usr/share/')
                debian.ln(solr_version_path, solr_home)
                debian.rm(archive)


@task
def configure():
    """
    Configure Solr
    """
    updated_confs = blueprint.upload('solr_home/', '/etc/solr/', user='solr')
    updated_init = blueprint.upload('init/', '/etc/init/', context={
        'memory': blueprint.get('memory', '512m')
    })

    if updated_confs or updated_init:
        restart()


@task
@parallel
def tail():
    with sudo('solr'), hide_prefix(), settings():
        try:
            run('tail -100f /var/log/solr/solr.log')
        except KeyboardInterrupt:
            pass
