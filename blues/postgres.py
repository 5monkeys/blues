import os
from fabric.decorators import task
from fabric.operations import run
from refabric.context_managers import sudo, silent
from refabric.contrib import debian
from refabric.state import blueprints

blueprint = blueprints.get(__name__)

postgres_root = '/etc/postgresql/9.1/main'

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
    context = pgtune()
    context.update(blueprint.get())



@task
def pgtune():
    conf_path = os.path.join(postgres_root, 'postgresql.conf')
    with sudo(), silent():
        output = run('pgtune -T Web -i {}'.format(conf_path)).strip()

        def parse(c):
            for line in c.splitlines():
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

        return dict(parse(output))
