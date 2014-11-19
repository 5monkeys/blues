import os

from fabric.decorators import task
from fabric.state import env
from fabric.utils import indent

from refabric.api import info
from blues import git

from . import blueprint
from .project import *
from .providers import get_provider
from .install import install, update_git, install_requirements


@task
def setup():
    """
    Create project user, paths, system dependencies and run upgrade
    """
    install()
    upgrade()


@task
def upgrade():
    """
    Reset git to HEAD, install pip requirements, upload web and worker conf
    """
    # Reset git repo
    info('Update source')
    previous_commit, current_commit = update_git()
    code_changed = previous_commit != current_commit

    # Check if requirements has changed
    requirements = blueprint.get('requirements', 'requirements.txt')
    commit_range = '{}..{}'.format(previous_commit, current_commit)
    requirements_changed, _, _ = git.diff_stat(git_repository_path(), commit_range, requirements)

    # Install repo requirements.txt
    info('Install requirements')
    if requirements_changed:
        install_requirements()
    else:
        info(indent('(requirements not changed...skipping)'))

    # Upload web and worker provider config
    upgrade_providers(force_reload=code_changed)


@task
def upgrade_providers(force_reload=False):
    """
    Render, upload and reload web & worker config
    """
    with sudo_project():
        providers = {}

        web_hosts = blueprint.get('web.hosts')
        web = blueprint.get('web.provider')
        if web:
            providers[web] = get_provider(web)

        worker_hosts = blueprint.get('worker.hosts')
        worker = blueprint.get('worker.provider')
        if worker:
            providers[worker] = get_provider(worker)

        if web and (not web_hosts or env.host_string in web_hosts):
            providers[web].upload_web_config()

        if worker and (not worker_hosts or env.host_string in worker_hosts):
            providers[worker].upload_worker_config()

    for provider in providers.values():
        if provider.updates or force_reload:
            provider.reload()


@task
def generate_nginx_conf(role='www'):
    """
    Genereate nginx site config for web daemon
    """
    name = blueprint.get('project')
    socket = blueprint.get('wsgi.socket', default='0.0.0.0:3030')
    host, _, port = socket.partition(':')
    if port:
        sockets = ['{}:{}'.format(host, port) for host in env.hosts]
    else:
        sockets = ['unix:{}'.format(socket)]

    context = {
        'name': name,
        'sockets': sockets,
        'domain': blueprint.get('wsgi.domain', default='_'),
        'ssl': blueprint.get('wsgi.ssl', False),
        'ip_hash': blueprint.get('wsgi.ip_hash', False)
    }
    template = 'nginx/site.conf'
    daemon = blueprint.get('wsgi.daemon')
    if daemon and daemon == 'uwsgi':
        template = 'nginx/uwsgi_site.conf'
    conf = blueprint.render_template(template, context)
    conf_dir = os.path.join(os.path.dirname(env['real_fabfile']), 'templates', role, 'nginx',
                            'sites-available')
    conf_path = os.path.join(conf_dir, '{}.conf'.format(name))

    if not os.path.exists(conf_dir):
        os.makedirs(conf_dir)

    with open(conf_path, 'w+') as f:
        f.write(conf)
