from fabric.contrib import files
from fabric.decorators import task

from refabric.api import run
from refabric.context_managers import sudo
from refabric.contrib import debian


@task
def setup():
    install()


def install():
    package_name = 'rabbitmq-server'
    debian.debconf_set_selections('%s rabbitmq-server/upgrade_previous note' % package_name)

    sources_list = "/etc/apt/sources.list"
    deb = "deb http://www.rabbitmq.com/debian/ testing main"
    with sudo():
        run("apt-key adv --keyserver pgp.mit.edu --recv-keys 0x056E8E56")
        files.append(sources_list, deb, shell=True)
        debian.apt_get('update')
        debian.apt_get('install', package_name)

