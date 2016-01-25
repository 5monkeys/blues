# coding=utf-8
"""
Neo4j Blueprint
===============

**Fabric environment:**

.. code-block:: yaml

    blueprints:
      - blues.neo4j

    settings:
      neo4j:
        password: "hej"
        # bind: 0.0.0.0  # Set the bind address specifically (Default: 0.0.0.0)
        # heap_size_mb: 512  # Set the heap size explicitly (Default: auto)

"""
import time
import base64

from fabric.decorators import task
from fabric.utils import abort

from refabric.api import info
from refabric.context_managers import sudo
from refabric.contrib import blueprints
from refabric.operations import run

from . import debian

__all__ = [
    'start', 'stop', 'restart', 'status', 'force_reload',
    'setup', 'configure', 'install', 'set_password',
]


blueprint = blueprints.get(__name__)

service_name = 'neo4j-service'
start = debian.service_task(service_name, 'start')
stop = debian.service_task(service_name, 'stop')
restart = debian.service_task(service_name, 'restart')
status = debian.service_task(service_name, 'status', show_output=True)
force_reload = debian.service_task(service_name, 'force-reload')


@task
def setup():
    """
    Install and configure Neo4j
    """
    install()
    configure()
    set_password()


@task
def install():
    """
    Install Neo4j
    """
    with sudo():
        from blues import java
        java.install()

        version = blueprint.get('version', '2.2')
        info('Adding apt repository for {} version {}', 'neo4j', version)

        repository = 'http://debian.neo4j.org/repo stable/'.format(version)
        debian.add_apt_repository(repository)

        info('Adding apt key for', repository)
        debian.add_apt_key('http://debian.neo4j.org/neotechnology.gpg.key')
        debian.apt_get_update()

        debian.apt_get('install', 'neo4j')

        # TODO: limits
        # And add these contents to /etc/security/limits.conf:
        # *       hard    memlock  unlimited
        # *       soft    memlock  unlimited
        # neo4j   soft    nofile  100000
        # neo4j   hard    nofile  100000
        # ubuntu  soft    nofile  100000
        # ubuntu  hard    nofile  100000

        # And uncomment this line in /etc/pam.d/su:
        # session    required   pam_limits.so

        # After that restart the server and validate the new limit
        # $ ulimit -n
        # 100000


@task
def configure():
    """
    Configure Neo4j
    """
    context = {
        'bind': blueprint.get('bind', '0.0.0.0'),
        'heap_size_mb': blueprint.get('heap_size_mb', 'auto'),
    }

    updated = False
    for f in [
        'logging.properties',
        'neo4j.properties',
        'neo4j-server.properties',
        'neo4j-wrapper.properties',
    ]:
        updated = bool(blueprint.upload(f, '/etc/neo4j/', context)) or updated

    if updated:
        restart()


@task
def set_password(old_password='neo4j', user='neo4j'):
    """
    Sets Neo4j password
    """

    new_password = blueprint.get('password')
    assert new_password

    info("Checking password")
    output = run(
        'curl -u %s:%s http://localhost:7474/user/%s' % (
            user, new_password, user))

    if '"username" : "%s"' % user in output:
        info("Password already set")

    else:
        if 'AuthorizationFailed' in output:
            info("Waiting 5 sec due to Jetty's bruteforce protection")
            time.sleep(5)

        info("Setting password")
        assert old_password

        # escape before sending in json via cli
        new_password = new_password.replace('\\', '\\\\')
        new_password = new_password.replace('"', '\\"')
        new_password = new_password.replace("'", "\\'")

        output = run(
            'curl -u %s:%s -X POST http://localhost:7474/user/%s/password '
            '-H "Accept: application/json; charset=UTF-8" '
            '-H "Content-Type: application/json" '
            '-d \'{"password" : "%s"}\' ' % (
                user, old_password, user, new_password))

        if 'AuthorizationFailed' in output:
            abort("Wrong current Neo4j password, cannot change it")

        elif '"username" : "%s"' % user not in output:
            abort("Unexpected response")
