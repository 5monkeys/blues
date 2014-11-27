"""
Java

Installs Java, currently restricted to version 7.

blueprints:
  - blues.java

"""
from fabric.decorators import task

from refabric.api import run, info
from refabric.context_managers import sudo

from . import debian

__all__ = ['setup']


@task
def setup():
    """
    Install Java
    """
    install()


def install():
    with sudo():
        lbs_release = debian.lbs_release()

        if lbs_release == '12.04':
            debian.add_apt_ppa('webupd8team/java')
            debian.debconf_set_selections('shared/accepted-oracle-license-v1-1 select true',
                                          'shared/accepted-oracle-license-v1-1 seen true')
            package = 'oracle-java7-installer'
        else:
            package = 'java7-jdk'

        info('Install Java 7 JDK')
        debian.apt_get('install', package)
