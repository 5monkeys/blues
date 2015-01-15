import os

from fabric.decorators import task
from fabric.state import env
from fabric.utils import indent

from refabric.utils import info

from .deploy import *
from .project import *
from .providers import get_providers

from .. import git
from ..app import blueprint

__all__ = []


@task
def setup():
    """
    Install project user, structure, env, source, dependencies and providers
    """
    install_project_structure()
    install_project_user()
    install_system_dependencies()
    install_or_update_source()
    install_virtualenv()
    install_requirements()
    install_providers()
    configure_providers()


@task
def configure():
    """
    Deploy and configure providers
    """
    code_changed = deploy(auto_reload=False)
    configure_providers(force_reload=code_changed)


@task
def deploy(auto_reload=True, force=False):
    """
    Reset source to configured branch and install requirements, if needed

    :return: Got new source?
    """
    # Reset git repo
    previous_commit, current_commit = update_source()
    code_changed = previous_commit != current_commit

    if code_changed or force:
        requirements = blueprint.get('requirements', 'requirements.txt')
        requirements_changed = False

        if not force:
            # Check if requirements has changed
            commit_range = '{}..{}'.format(previous_commit, current_commit)
            requirements_changed, _, _ = git.diff_stat(git_repository_path(), commit_range, requirements)

        # Install repo requirements.txt
        info('Install requirements {}', requirements)
        if requirements_changed or force:
            install_requirements()
        else:
            info(indent('(requirements not changed in {}...skipping)'), commit_range)

        if auto_reload:
            reload()

    return code_changed


@task
def start():
    """
    Start all application providers on current host
    """
    providers = get_providers(env.host_string)
    for provider in providers.values():
        provider.start()


@task
def stop():
    """
    Stop all application providers on current host
    """
    providers = get_providers(env.host_string)
    for provider in providers.values():
        provider.stop()


@task
def reload():
    """
    Reload all application providers on current host
    """
    providers = get_providers(env.host_string)
    for provider in providers.values():
        provider.reload()


@task
def configure_providers(force_reload=False):
    """
    Render, upload and reload web & worker config
    """
    with sudo_project():
        providers = get_providers(env.host_string)
        if 'web' in providers:
            providers['web'].configure_web()
        if 'worker' in providers:
            providers['worker'].configure_worker()

    for provider in providers.values():
        if provider.updates or force_reload:
            provider.reload()

    return providers


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
        'domain': blueprint.get('web.domain', default='_'),
        'ssl': blueprint.get('web.ssl', False),
        'ip_hash': blueprint.get('web.ip_hash', False)
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
