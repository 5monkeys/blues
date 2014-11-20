import os

from fabric.decorators import task

from refabric.api import run, info
from refabric.context_managers import sudo, hide_prefix
from refabric.contrib import blueprints

from . import debian
from . import python

__all__ = ['start', 'stop', 'restart', 'reload', 'setup', 'configure', 'top']


blueprint = blueprints.get(__name__)

log_path = '/var/log/uwsgi'
tmpfs_path = '/run/uwsgi/'

start = debian.service_task('uwsgi', 'start')
stop = debian.service_task('uwsgi', 'stop')
restart = debian.service_task('uwsgi', 'restart')
reload = debian.service_task('uwsgi', 'reload')


@task
def setup():
    """
    Install uWSGI system wide and upload vassals
    """
    install()
    configure()


def install():
    with sudo():
        # Ensure python (pip) is installed
        python.install()

        # PIP install system wide uWSGI
        package = 'uwsgi'
        version = blueprint.get('version')
        if version:
            package += '=={}'.format(version)
        info('Installing: {} ({})', 'uWSGI', version if version else 'latest')
        python.pip('install', package)
        python.pip('install', 'uwsgitop', 'gevent')

        # Create group
        debian.groupadd('app-data', gid_min=10000)

        # Create directories
        debian.mkdir(log_path, owner='root', group='app-data', mode=1775)
        debian.mkdir(tmpfs_path, owner='root', group='app-data', mode=1775)


@task
def configure():
    """
    Upload vassals
    """
    with sudo():
        # Upload templates
        blueprint.upload('init/', '/etc/init/')


@task
def top():
    """
    Launch uwsgitop for project stats socket
    """
    # TODO: fix missing output
    with sudo(), hide_prefix():
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
    """
    Get limit_as setting depending on server memory in GB
    """
    return gb_memory * 512
