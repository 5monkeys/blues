"""
Java
====

Installs Java, currently restricted to version 7.

**Fabric environment:**

.. code-block:: yaml

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
        elif lbs_release >= '16.04':
            package = 'default-jdk'
        elif lbs_release >= '14.04':
            package = 'openjdk-7-jdk'
        else:
            package = 'java7-jdk'

        if package != 'default-jdk':
            info('Install Java 7 JDK')
        else:
            info('Install default Java JDK')

        debian.apt_get('install', package)
