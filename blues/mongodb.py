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
        replSet: webscale
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


def get_version():
    r = _client_exec('db.version()', auth=False)
    return tuple(map(int, r.split('.'))[:2])


def upload_conf(auth=None):
    context = {
        'bind': blueprint.get('bind', '127.0.0.1'),
        'auth': blueprint.get('auth', True) if auth is None else auth,
    }
    return blueprint.upload('mongodb.conf', '/etc/mongodb.conf', context)


@task
def configure():
    """
    Configure mongodb
    """
    uploads = [
        upload_conf()
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
    if not blueprint.get('auth', True) or blueprint.get('slave'):
        return

    upload_conf(auth=False) and restart()

    admin = blueprint.get('admin', {})
    roles = [
        {'role': 'userAdminAnyDatabase', 'db': 'admin'},
        {'role': 'readWriteAnyDatabase', 'db': 'admin'},
        {'role': 'dbAdminAnyDatabase', 'db': 'admin'},
        {'role': 'clusterAdmin', 'db': 'admin'}
    ]

    # Restart mongod without the auth flag
    _ensure_user('admin', admin['user'], admin['password'], roles, auth=False)

    upload_conf(auth=True) and restart()


@task
def setup_schemas():
    """
    Creates database schemas and grant user privileges.
    """
    if blueprint.get('slave'):
        return
    schemas = blueprint.get('schemas', {})
    for schema, config in schemas.iteritems():
        info('Setting up schema {}', schema)
        roles = [{'role': 'readWrite', 'db': schema}]
        _ensure_user(schema, config['user'], config['password'], roles)


def _add_user(schema, user, password, roles, auth=True):
    roles = [r['role'] for r in roles]
    roles = json.dumps(roles).replace('"', '\'')
    _client_exec("""
        use %(schema)s;
        db.removeUser('%(user)s');
        db.addUser({
            user: '%(user)s',
            pwd: '%(password)s',
            roles: %(roles)s
        })
    """, user=user, password=password, roles=roles, auth=auth, schema=schema)


def _ensure_user(schema, user, password, roles, auth=True):
    info('Creating/updating user {}', user)

    version = get_version()
    if version < (2, 4):
        raise NotImplementedError

    elif version < (2, 6):
        return _add_user(schema, user, password, roles, auth=auth)

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
