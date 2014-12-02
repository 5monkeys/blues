"""
Postgres Blueprint
==================

**Fabric environment:**

.. code-block:: yaml

    blueprints:
      - blues.postgres

    settings:
      postgres:
        schemas:
          some_schema_name:    # The schema name
            user: foo          # Username to connect to schema
            password: bar      # Password to connect to schema

"""
import os
from datetime import datetime

from fabric.contrib import files
from fabric.decorators import task
from fabric.operations import prompt
from fabric.state import env

from refabric.api import run, info
from refabric.context_managers import sudo, silent
from refabric.contrib import blueprints

from . import debian

__all__ = ['start', 'stop', 'restart', 'reload', 'setup', 'configure',
           'setup_schemas', 'generate_pgtune_conf', 'dump']


blueprint = blueprints.get(__name__)

postgres_root = '/etc/postgresql/9.1/main/'

start = debian.service_task('postgresql', 'start')
stop = debian.service_task('postgresql', 'stop')
restart = debian.service_task('postgresql', 'restart')
reload = debian.service_task('postgresql', 'reload')


def install():
    with sudo():
        debian.apt_get('install',
                       'postgresql',
                       'postgresql-server-dev-9.1',
                       'libpq-dev',
                       'postgresql-contrib-9.1',
                       'pgtune')


@task
def setup():
    """
    Install, configure Postgresql and create schemas
    """
    install()
    # Bump shared memory limits
    setup_shared_memory()

    # Generate pgtune.conf
    generate_pgtune_conf()

    # Upload templates
    configure()

    # Create schemas and related users
    setup_schemas()


@task
def configure():
    """
    Configure Postgresql
    """
    updates = blueprint.upload('./', postgres_root)
    if updates:
        restart()


@task
def setup_schemas(drop=False):
    """
    Create database schemas and grant user privileges

    :param drop: Drop existing schemas before creation
    """
    schemas = blueprint.get('schemas', [])
    with sudo('postgres'):
        for schema, config in schemas:
            user, password, schema = config['user'], config['password'], config['schema']
            info('Creating user {}', user)
            _client_exec("CREATE USER %(user)s WITH PASSWORD '%(password)s'",
                         user=user, password=password)
            if drop:
                info('Droping schema {}', schema)
                _client_exec('DROP DATABASE %(name)s', name=schema)
            info('Creating schema {}', schema)
            _client_exec('CREATE DATABASE %(name)s', name=schema)
            info('Granting user {} to schema {}'.format(user, schema))
            _client_exec("GRANT ALL PRIVILEGES ON DATABASE %(schema)s to %(user)s",
                         schema=schema, user=user)


def _client_exec(cmd, **kwargs):
    with sudo('postgres'):
        schema = kwargs.get('schema', 'template1')
        return run("echo \"%s;\" | psql -d %s" % (cmd % kwargs, schema))


def setup_shared_memory():
    """
    http://leopard.in.ua/2013/09/05/postgresql-sessting-shared-memory/
    """
    sysctl_path = '/etc/sysctl.conf'
    shmmax_configured = files.contains(sysctl_path, 'kernel.shmmax')
    shmall_configured = files.contains(sysctl_path, 'kernel.shmall')
    if not any([shmmax_configured, shmall_configured]):
        page_size = debian.page_size()
        phys_pages = debian.phys_pages()
        shmall = phys_pages / 2
        shmmax = shmall * page_size

        shmmax_str = 'kernel.shmmax = {}'.format(shmmax)
        shmall_str = 'kernel.shmall = {}'.format(shmall)
        with sudo():
            files.append(sysctl_path, shmmax_str, partial=True)
            files.append(sysctl_path, shmall_str, partial=True)
            run('sysctl -p')
        info('Added **{}** to {}', shmmax_str, sysctl_path)
        info('Added **{}** to {}', shmall_str, sysctl_path)


@task
def generate_pgtune_conf(role='db'):
    """
    Run pgtune and create pgtune.conf

    :param role: Which fabric role to place local pgtune.conf template under
    """
    conf_path = os.path.join(postgres_root, 'postgresql.conf')
    with sudo(), silent():
        output = run('pgtune -T Web -i {}'.format(conf_path)).strip()

        def parse(c):
            lines = [l for l in c.splitlines() if '# pgtune' in l]
            for line in lines:
                try:
                    comment = line.index('#')
                    line = line[:comment]
                except ValueError:
                    pass
                clean = lambda s: s.strip('\n\r\t\'" ')
                key, _, value = line.partition('=')
                key, value = map(clean, (key, value))
                if key:
                    yield key, value or None

        tune_conf = dict(parse(output))
        tune_conf.update(blueprint.get('pgtune', {}))
        tune_conf = '\n'.join((' = '.join(item)) for item in tune_conf.iteritems())
        conf_dir = os.path.join(os.path.dirname(env['real_fabfile']), 'templates', role, 'postgres')
        conf_path = os.path.join(conf_dir, 'pgtune.conf')

        if not os.path.exists(conf_dir):
            os.makedirs(conf_dir)

        with open(conf_path, 'w+') as f:
            f.write(tune_conf)


@task
def dump(schema=None):
    """
    Dump and download all configured, or given, schemas.

    :param schema: Specific shema to dump and download.
    """
    if not schema:
        schemas = blueprint.get('schemas', {}).keys()
        for i, schema in enumerate(schemas, start=1):
            print("{i}. {schema}".format(i=i, schema=schema))
        valid_indices = '[1-{}]+'.format(len(schemas))
        schema_choice = prompt('Select schema to dump:', default='1', validate=valid_indices)
        schema = schemas[int(schema_choice)-1]

    with sudo('postgres'):
        now = datetime.now().strftime('%Y-%m-%d')
        output_file = '/tmp/{}_{}.backup'.format(schema, now)
        filename = os.path.basename(output_file)

        options = dict(
            format='tar',
            output_file=output_file,
            schema=schema
        )

        info('Dumping schema {}...', schema)
        run('pg_dump -c -F {format} -f {output_file} {schema}'.format(**options))

        info('Downloading dump...')
        local_file = '~/{}'.format(filename)
        files.get(output_file, local_file)

    with sudo(), silent():
        debian.rm(output_file)

    info('New smoking hot dump at {}', local_file)
