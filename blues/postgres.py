from datetime import datetime
from functools import partial
import os
from fabric.contrib import files
from fabric.decorators import task
from fabric.state import env
from fabric.utils import warn
from refabric.context_managers import sudo, silent
from refabric.contrib import debian, blueprints
from refabric.operations import run
from refabric.utils import info

blueprint = blueprints.get(__name__)

postgres_root = '/etc/postgresql/9.1/main'

start = task(partial(debian.service, 'postgresql', 'start', check_status=False))
stop = task(partial(debian.service, 'postgresql', 'stop', check_status=False))
restart = task(partial(debian.service, 'postgresql', 'restart', check_status=False))
reload = task(partial(debian.service, 'postgresql', 'reload', check_status=False))


@task
def install():
    with sudo():
        debian.apt_get('install',
                       'postgresql',
                       'postgresql-server-dev-9.1',
                       'libpq-dev',
                       'postgresql-contrib-9.1',
                       'pgtune')


@task
def upgrade():
    # Bump shared memory limits
    setup_shared_memory()

    # Generate pgtune.conf
    generate_pgtune_conf()

    updates = blueprint.upload('./', postgres_root)
    if updates:
        restart()

@task
def setup_databases():
    databases = blueprint.get('databases', [])
    with sudo('postgres'):
        for database in databases:
            print database
            with sudo('postgres'):
                _client_exec("CREATE USER %(user)s WITH PASSWORD '%(password)s'",
                             user=database['user'], password=database['password'])
                run('createdb -O {} {}'.format(database['user'], database['schema']))


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
def dump_all():
    databases = blueprint.get('databases')

    if not databases:
        warn('No databases to dump found among your templates')

    else:
        for db_conf in databases:
            dump(db_conf['schema'])


def dump(schema, format='tar', output_file=None):
    with sudo('postgres'):
        now = datetime.now().strftime('%Y-%m-%d')
        output_file = output_file or ('/tmp/%s_%s.backup' % (schema, now))
        filename = os.path.basename(output_file)

        options = dict(
            format=format,
            output_file=output_file,
            schema=schema
        )

        info('Dumping schema {}...', schema)
        run('pg_dump -c -F %(format)s -f %(output_file)s %(schema)s ' % options)

        info('Downloading dump...')
        local_file = '~/%s' % filename
        files.get(output_file, local_file)

        info('New smoking hot dump at {}', local_file)
