import os
from functools import partial
from fabric.decorators import task
from refabric.context_managers import sudo, hide_prefix
from refabric.contrib import debian, blueprints
from refabric.operations import run
from refabric.utils import info

blueprint = blueprints.get(__name__)

log_path = '/var/log/uwsgi'
tmpfs_path = '/run/uwsgi/'

start = task(partial(debian.service, 'uwsgi', 'start'))
stop = task(partial(debian.service, 'uwsgi', 'stop'))
restart = task(partial(debian.service, 'uwsgi', 'restart'))
reload = task(partial(debian.service, 'uwsgi', 'reload'))


@task
def setup():
    install()
    upgrade()


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


def get_worker_count(cores):
    """
    Get number of workers to run depending on server core count
    """
    return cores * 2


def get_cpu_affinity(cores, workers=None):
    """
    Get CPU affinity depending on server core count
    http://lists.unbit.it/pipermail/uwsgi/2011-March/001594.html
    """
    workers = workers or get_worker_count(cores)
    if workers <= 4:
        return 1
    elif cores < 8:
        return 2
    else:
        return 3


def get_max_requests(gb_memory):
    """
    Get max_requests setting depending on server memory in GB
    """
    return gb_memory * 2000


def get_reload_on_as(gb_memory):
    """
    Get reload_on_as setting depending on server memory in GB
    """
    return gb_memory * 256


def get_reload_on_rss(gb_memory):
    """
    Get reload_on_rss setting depending on server memory in GB
    """
    return get_reload_on_as(gb_memory) / 2


def get_limit_as(gb_memory):
    return gb_memory * 512
