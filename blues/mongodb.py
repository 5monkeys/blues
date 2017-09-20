"""
MongoDB Blueprint
=================

**Fabric environment:**

.. code-block:: yaml

    blueprints:
      - blues.mongodb

    settings:
      mongodb:
        # bind: 0.0.0.0  # Set the bind address specifically (Default: 127.0.0.1)
        keyfile: 'mongodb-keyfile'
        admin:
          user: admin          # Superuser username
          password: foobar123  # Superuser password
        schemas:
          some_schema_name:    # The schema name
            user: foo          # Username to connect to schema
            password: bar      # Password to connect to schema (optional)

"""
import json

from fabric.decorators import task

from refabric.context_managers import sudo
from refabric.contrib import blueprints
from refabric.api import run, info

from . import debian

__all__ = ['start', 'stop', 'restart', 'setup', 'configure', 'setup_schemas',
           'setup_admin']


blueprint = blueprints.get(__name__)

start = debian.service_task('mongodb', 'start')
stop = debian.service_task('mongodb', 'stop')
restart = debian.service_task('mongodb', 'restart')


@task
def setup():
    """
    Install and configure mongodb
    """
    install()
    configure()
    if not blueprint.get('slave'):
        setup_admin()
        setup_schemas()


def install():
    with sudo():
        debian.apt_get('install', 'mongodb')


@task
def configure(auth=None):
    """
    Configure mongodb
    """
    context = {
        'bind': blueprint.get('bind', '127.0.0.1'),
        'auth': blueprint.get('auth', True),
    }
    if auth is not None:
        context['auth'] = auth
    uploads = [
        blueprint.upload('mongodb.conf', '/etc/mongodb.conf', context)
    ]
    keyfile = blueprint.get('keyfile')
    if keyfile is not None:
        uploaded_file = blueprint.upload(keyfile, '/var/lib/mongodb/keyfile')
        uploads.append(uploaded_file)
        run('chmod 600 /var/lib/mongodb/keyfile')
        run('chown mongodb:nogroup /var/lib/mongodb/keyfile')
    if any(uploads):
        restart()


@task
def setup_admin():
    """
    Creates a superuser account.
    """
    admin = blueprint.get('admin', {})
    roles = [
        {'role': 'userAdminAnyDatabase', 'db': 'admin'},
        {'role': 'readWriteAnyDatabase', 'db': 'admin'},
        {'role': 'dbAdminAnyDatabase', 'db': 'admin'},
        {'role': 'clusterAdmin', 'db': 'admin'}
    ]

    # Restart mongod without the auth flag
    _ensure_user('admin', admin['user'], admin['password'], roles, auth=False)


@task
def setup_schemas():
    """
    Creates database schemas and grant user privileges.
    """
    schemas = blueprint.get('schemas', {})
    for schema, config in schemas.iteritems():
        info('Setting up schema {}', schema)
        roles = [{'role': 'readWrite', 'db': schema}]
        _ensure_user(schema, config['user'], config['password'], roles)


def _ensure_user(schema, user, password, roles, auth=True):
    info('Creating/updating user {}', user)
    roles = json.dumps(roles).replace('"', '\'')
    r = _client_exec("""
        use %(schema)s;
        db.updateUser('%(user)s', {
            pwd: '%(password)s',
            roles: %(roles)s
        })
    """, user=user, password=password, roles=roles, auth=auth, schema=schema)
    if 'not found' in r:
        _client_exec("""
            use %(schema)s;
            db.createUser({
                user: '%(user)s',
                pwd: '%(password)s',
                roles: %(roles)s
            })
        """, user=user, password=password, roles=roles, auth=auth, schema=schema
        )


def _client_exec(cmd, auth=True, **kwargs):
    with sudo():
        schema = kwargs.get('schema')
        cmd = "echo \"%s;\" | mongo --quiet" % (cmd % kwargs)
        if auth:
            admin = blueprint.get('admin')
            extra = " -u \"%s\" -p \"%s\" --authenticationDatabase \"admin\""
            cmd += extra % (admin['user'], admin['password'])
        return run(cmd)
