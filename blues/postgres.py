"""
Postgres Blueprint
==================

**Fabric environment:**

.. code-block:: yaml

    blueprints:
      - blues.postgres

    settings:
      postgres:
        version: 9.3           # PostgreSQL version (required)
        # bind: *              # What IP address(es) to listen on, use '*' for all (Default: localhost)
        # allow: 10.0.0.0/24   # Additionally allow connections from netmask (Default: 127.0.0.1/32)
        schemas:
          some_schema_name:        # The schema name
            user: foo              # Username to connect to schema
            password: bar          # Password to connect to schema (optional)
            dump_options:          # Specify extra options passed to pg_dump (optional)
              exclude_table_data:  # Exclude data from table (optional)
                - some_table
                - another_table

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
           'setup_schemas', 'generate_pgtune_conf', 'dump', 'install',
           'download_pgtune', 'stop_all']


blueprint = blueprints.get(__name__)

version = lambda: blueprint.get('version', '9.1')

start = debian.service_task('postgresql', 'start %s' % version())
stop = debian.service_task('postgresql', 'stop %s' % version())
stop_all = debian.service_task('postgresql', 'stop')
restart = debian.service_task('postgresql', 'restart %s' % version())
reload = debian.service_task('postgresql', 'reload %s' % version())

postgres_root = lambda *a: os.path.join('/etc/postgresql/{}/main/'.format(version()), *a)
pgtune_root = '/usr/local/src/pgtune'


@task
def install(add_repo=None):
    with sudo():
        v = version()
        if add_repo is None:
            add_repo = (debian.lsb_release() == '14.04' and
                        tuple(map(int, str(v).split('.'))) >= (9, 4))
        if add_repo:
            add_repository()

        debian.apt_get('install',
                       'postgresql-{}'.format(v),
                       'postgresql-server-dev-{}'.format(v),
                       'libpq-dev',
                       'postgresql-contrib-{}'.format(v),
                       )
        download_pgtune()


@task
def download_pgtune():
    run('rm -r {} || true'.format(pgtune_root))
    run('mkdir -p {}'.format(pgtune_root))

    run('curl https://codeload.github.com/andreif/pgtune/legacy.tar.gz/'
        'allthethings | tar xzv -C {} --strip=1'.format(pgtune_root))

    run('python {}/pgtune --doctest --help'.format(pgtune_root))

    info('Downloaded pgtune to {}/'.format(pgtune_root))


def add_repository():
    name = debian.lsb_codename()
    info('Adding postgres {} apt repository...', name)
    repo = 'https://apt.postgresql.org/pub/repos/apt/ {}-pgdg main'.format(name)
    debian.add_apt_key('https://www.postgresql.org/media/keys/ACCC4CF8.asc')
    debian.add_apt_repository(repository=repo)
    debian.apt_get_update()


def install_postgis(v=None):
    if not v:
        v = version()

    info('Installing postgis...')
    debian.apt_get('install', 'postgis',
                   'postgresql-{}-postgis-scripts'.format(v))


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
    context = {
        'listen_addresses': blueprint.get('bind', 'localhost'),
        'host_all_allow': blueprint.get('allow', None)
    }
    updates = [
        blueprint.upload(os.path.join('.', 'pgtune.conf'),
                         postgres_root(),
                         user='postgres'),
        blueprint.upload(os.path.join('.', 'pg_hba.conf'),
                         postgres_root(),
                         context=context,
                         user='postgres'),
        blueprint.upload(os.path.join('.',
                                      'postgresql-{}.conf'.format(version())),
                         postgres_root('postgresql.conf'),
                         context=context,
                         user='postgres')
    ]

    if any(updates):
        restart()


@task
def setup_schemas(drop=False):
    """
    Create database schemas and grant user privileges

    :param drop: Drop existing schemas before creation
    """
    schemas = blueprint.get('schemas', {})
    extensions = blueprint.get('extensions', [])

    if 'postgis' in extensions:
        install_postgis(v=version())

    with sudo('postgres'):
        for schema, config in schemas.iteritems():
            user, password = config['user'], config.get('password')
            info('Creating user {}', user)
            if password:
                _client_exec("CREATE ROLE %(user)s WITH PASSWORD '%(password)s'"
                             " LOGIN",
                             user=user,
                             password=password)
            else:
                _client_exec("CREATE ROLE %(user)s LOGIN", user=user)
            if drop:
                info('Droping schema {}', schema)
                _client_exec('DROP DATABASE %(name)s', name=schema)
            info('Creating schema {}', schema)
            _client_exec('CREATE DATABASE %(name)s', name=schema)
            info('Granting user {} to schema {}'.format(user, schema))
            _client_exec("GRANT ALL PRIVILEGES"
                         " ON DATABASE %(schema)s to %(user)s",
                         schema=schema, user=user)

            for ext in extensions:
                info('Creating extension {}'.format(ext))
                _client_exec("CREATE EXTENSION IF NOT EXISTS %(ext)s", ext=ext, schema=schema)


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
def generate_pgtune_conf(role='db', **options):
    """
    Run pgtune and create pgtune.conf

    :param role: Which fabric role to place local pgtune.conf template under
    """
    info('Generating pgtune conf')

    options.setdefault('type', 'Web')
    options.setdefault('version', version())
    options.setdefault('input-config', postgres_root('postgresql.conf'))
    options.setdefault('settings', pgtune_root)

    options = ' '.join(
        '--{}="{}"'.format(key, value)
        for key, value in options.items()
    )

    with sudo(), silent():
        info('options: ' + options)
        output = run('{}/pgtune {}'.format(pgtune_root, options)).strip()
        output = output.rpartition('\n# pgtune')[2].partition('\n')[2]

        def parse(c):
            for line in c.splitlines():
                line = line.split('#')[0].strip()
                if line:
                    clean = lambda s: s.strip('\n\r\t\'" ')
                    key, _, value = line.partition('=')
                    key, value = map(clean, (key, value))
                    if key:
                        yield key, value or None

        tune_conf = dict(parse(output))
        tune_conf.update(blueprint.get('pgtune', {}))
        tune_conf = '\n'.join(' = '.join(item)
                              for item in sorted(tune_conf.iteritems()))
        conf_dir = os.path.join(
            os.path.dirname(env['real_fabfile']),
            'templates',
            role,
            'postgres')
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
        schema_choice = prompt('Select schema to dump:', default='1',
                               validate=valid_indices)
        schema = schemas[int(schema_choice) - 1]
        dump_options = blueprint[schema].get(
            'dump_options',
            blueprint.get('dump_options', {})
        )

    with sudo('postgres'):
        now = datetime.now().strftime('%Y-%m-%d')
        output_file = '/tmp/{}_{}.backup'.format(schema, now)
        filename = os.path.basename(output_file)

        options = [
            '-c',
            '-F', 'tar',
            'f', output_file
        ]

        if dump_options:
            exclude_table_data = dump_options.get('exclude_table_data', [])
            if exclude_table_data:
                options += ['--exclude-table-data=' + table for table in exclude_table_data]

        info('Dumping schema {}...', schema)
        run('pg_dump ' + ' '.join(options + [schema]))

        info('Downloading dump...')
        local_file = '~/{}'.format(filename)
        files.get(output_file, local_file)

    with sudo(), silent():
        debian.rm(output_file)

    info('New smoking hot dump at {}', local_file)
