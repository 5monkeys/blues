"""
Percona (MySQL) Blueprint
=========================

**Fabric environment:**

.. code-block:: yaml

    blueprints:
      - blues.percona

    settings:
      percona:
        schemas:
          some_schema_name:    # The schema name
            user: foo          # Username to connect to schema
            password: bar      # Password to connect to schema
            host: 11.22.33.%s  # Allowed host mask to connect from (Default: 127.0.0.1)
        # bind: 0.0.0.0        # Set the bind address specifically (Default: 127.0.0.1)

"""
import ConfigParser
import random
from itertools import imap
from string import ascii_lowercase, digits
from datetime import datetime
from StringIO import StringIO

import fabric.contrib.files
import fabric.operations
from fabric.context_managers import settings, shell_env
from fabric.decorators import task
from fabric.operations import prompt, os
from fabric.utils import warn

from refabric.api import run
from refabric.context_managers import sudo, silent, hide_prefix
from refabric.contrib import blueprints
from refabric.utils import info

from blues import debian


blueprint = blueprints.get(__name__)

postgres_root = '/etc/mysql/'

start = debian.service_task('mysql', 'start')
stop = debian.service_task('mysql', 'stop')
restart = debian.service_task('mysql', 'restart')
reload = debian.service_task('mysql', 'reload')


def generate_password(length=8):
    return ''.join(imap(lambda i: random.choice(ascii_lowercase + digits), range(length)))


def install():
    with sudo():
        # Generate a root password and save it in root home
        root_conf_path = '/root/.my.cnf'
        if not fabric.contrib.files.exists(root_conf_path):
            root_pw = generate_password()
            blueprint.upload('root_my.cnf', '/root/.my.cnf', {'password': root_pw})
            debian.chmod('/root/.my.cnf', mode=600)
        else:
            # TODO: use fabric.operations.get instead of cat when up to date with upstream
            with silent():
                output = run('cat {}'.format(root_conf_path))
            fd = StringIO(output)
            config_parser = ConfigParser.RawConfigParser()
            config_parser.readfp(fd)
            root_pw = config_parser.get('client', 'password')

        # Install external PPA
        info('Adding apt key for {}', __name__)
        run("apt-key adv --keyserver keys.gnupg.net --recv-keys 1C4CBDCDCD2EFD2A")

        info('Adding apt repository for {}', __name__)
        debian.add_apt_repository('http://repo.percona.com/apt trusty main')
        debian.apt_get_update()

        # Percona/MySQL base dependencies
        dependencies = (
            'percona-server-server',
            'percona-server-client',
            'libmysqlclient-dev',
            'mysqltuner'
        )

        # Configure debconf to autoset root password on installation prompts
        server_package = dependencies[0]
        debian.debconf_communicate('PURGE', server_package)
        with silent():
            debian.debconf_set_selections(
                '{}/root_password password {}'.format(server_package, root_pw),
                '{}/root_password_again password {}'.format(server_package, root_pw)
            )

        # Install package
        info('Installing {}', __name__)
        debian.apt_get('install', *dependencies)
        debian.debconf_communicate('PURGE', server_package)

        # Auto-answer mysql_secure_installation prompts
        prompts = {
            'Enter current password for root (enter for none): ': root_pw,
            'Change the root password? [Y/n] ': 'n',
            'Remove anonymous users? [Y/n] ': 'Y',
            'Disallow root login remotely? [Y/n] ': 'Y',
            'Remove test database and access to it? [Y/n] ': 'Y',
            'Reload privilege tables now? [Y/n] ': 'Y'

        }
        # Run mysql_secure_installation to remove test-db and remote root login
        with settings(prompts=prompts):
            run('mysql_secure_installation')


@task
def setup():
    """
    Install, configure percona server and create schemas
    """
    # Setup percona/mysql
    install()
    # Upload config
    configure()
    # Create schemas and related users
    setup_schemas()


@task
def configure():
    """
    Configure Percona
    """
    context = {'bind': blueprint.get('bind')}
    uploads = blueprint.upload('my.cnf', '/etc/mysql/my.cnf', context=context)
    if uploads:
        warn('The mysql config has changed!')
        answer = prompt('Type "yes" to restart, or "no" to skip:',
                        default='no', validate='yes|no')
        if answer == 'yes':
            restart()


@task
def setup_schemas(drop=False):
    """
    Create database schemas and grant user permissions

    :param drop: Drop existing schemas before creation
    """
    schemas = blueprint.get('schemas', {})
    for schema, config in schemas.iteritems():
        user, password = config['user'], config['password']
        host = config.get('host', 'localhost')
        if drop:
            info('Dropping schema {}', schema)
            client_exec('DROP DATABASE IF EXISTS {name}', name=schema)

        info('Creating schema {}', schema)
        create_db_cmd = 'CREATE DATABASE IF NOT EXISTS {name} ' \
                        'CHARACTER SET UTF8 COLLATE UTF8_UNICODE_CI;'
        client_exec(create_db_cmd, name=schema)

        grant(schema, user, password, host=host)


def grant(schema, user, password, privs='ALL', host='localhost'):
    if not '.' in schema:
        schema = "%s.*" % schema
    info('Granting user {} @ {} to schema {}'.format(user, host, schema))
    grant_cmd = "GRANT {privs} ON {schema} TO '{user}'@'{host}' IDENTIFIED BY '{password}';"
    client_exec(grant_cmd, privs=privs, schema=schema, user=user, host=host, password=password)


def client_exec(cmd, **kwargs):
    with shell_env():
        return run('sudo su root -c "mysql -e \\"{}\\""'.format(cmd.format(**kwargs)), shell=False)


@task
def mysqltuner():
    """
    Run mysqltuner
    """
    with hide_prefix():
        run('sudo su root -c mysqltuner')


@task
def dump(schema=None, ignore_tables=''):
    """
    Dump and download a schema.

    :param schema: Specific shema to dump and download.
    :param ignore_tables: Tables to skip, separated by | (pipe)
    """
    if not schema:
        schemas = blueprint.get('schemas', {}).keys()
        for i, schema in enumerate(schemas, start=1):
            print("{i}. {schema}".format(i=i, schema=schema))
        valid_indices = '[1-{}]+'.format(len(schemas))
        schema_choice = prompt('Select schema to dump:', default='1', validate=valid_indices)
        schema = schemas[int(schema_choice)-1]

    now = datetime.now().strftime('%Y-%m-%d')
    output_file = '/tmp/{}_{}.backup.gz'.format(schema, now)
    filename = os.path.basename(output_file)

    info('Dumping schema {}...', schema)
    extra_args = []
    for table in ignore_tables.split('|'):
        extra_args.append('--ignore-table={}.{}'.format(schema, table))

    dump_cmd = 'mysqldump {} {} | gzip > {}'.format(schema, ' '.join(extra_args), output_file)

    run('sudo su root -c "{}"'.format(dump_cmd))
    info('Downloading dump...')
    local_file = '~/%s' % filename
    fabric.contrib.files.get(output_file, local_file)

    with sudo(), silent():
        debian.rm(output_file)

    info('New smoking hot dump at {}', local_file)
