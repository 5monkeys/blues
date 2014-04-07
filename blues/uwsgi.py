from functools import partial
import os
from fabric.decorators import task
from refabric.context_managers import sudo, hide_prefix
from refabric.contrib import debian, blueprints
from refabric.operations import run
from refabric.utils import info

blueprint = blueprints.get(__name__)

log_path = '/var/log/uwsgi'
tmpfs_path = '/run/uwsgi/'


@task
def install():
    with sudo():
        # PIP install system wide uWSGI
        cmd = 'pip install uwsgi'
        version = blueprint.get('version')
        if version:
            cmd += '=={}'.format(version)
        info('Installing: {} ({})', 'uWSGI', version if version else 'latest')
        run(cmd)
        run('pip install uwsgitop')

        # Create group
        debian.groupadd('app-data', gid_min=10000)

        # Create directories
        debian.mkdir(log_path, owner='root', group='app-data', mode=1775)
        debian.mkdir(tmpfs_path, owner='root', group='app-data', mode=1775)


@task
def upgrade():
    with sudo():
        # Upload templates
        blueprint.upload('init/', '/etc/init/')


@task
def top():
    # TODO: fix missing output
    with hide_prefix():
        stats_path = os.path.join(tmpfs_path, '{}-stats.sock'.format(blueprint.get('project')))
        run('uwsgitop {}'.format(stats_path))


start = task(partial(debian.service, 'uwsgi', 'start'))
stop = task(partial(debian.service, 'uwsgi', 'stop'))
restart = task(partial(debian.service, 'uwsgi', 'restart'))
reload = task(partial(debian.service, 'uwsgi', 'reload'))
