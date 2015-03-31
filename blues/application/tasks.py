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

    :param bool auto_reload: Reload application providers if source has changed
    :param bool force: Force install of requirements
    :return bool: Source code has changed?
    """
    # Reset git repo
    previous_commit, current_commit = update_source()
    code_changed = current_commit is not None and previous_commit != current_commit

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
def deployed():
    """
    Show deployed and last origin commit
    """
    with sudo_project():
        repository_path = git_repository_path()
        git.fetch(repository_path)

        head_commit, head_message = git.log(repository_path)[0]
        origin_commit, origin_message = git.log(repository_path, commit='origin')[0]

        info('Deployed commit: {} - {}', head_commit[:7], head_message)
        if head_commit == origin_commit:
            info(indent('(up-to-date with origin)'))
        else:
            info('Pending release: {} - {}', origin_commit[:7], origin_message)

        return head_commit, origin_commit


@task
def start():
    """
    Start all application providers on current host
    """
    providers = get_providers(env.host_string)
    for provider in set(providers.values()):
        provider.start()


@task
def stop():
    """
    Stop all application providers on current host
    """
    providers = get_providers(env.host_string)
    for provider in set(providers.values()):
        provider.stop()


@task
def reload():
    """
    Reload all application providers on current host
    """
    providers = get_providers(env.host_string)
    for provider in set(providers.values()):
        provider.reload()


@task
def configure_providers(force_reload=False):
    """
    Render, upload and reload web & worker config

    :param bool force_reload: Force reload of providers, even if not updated
    :return dict: Application providers for current host
    """
    with sudo_project():
        providers = get_providers(env.host_string)
        if 'web' in providers:
            providers['web'].configure_web()
        if 'worker' in providers:
            providers['worker'].configure_worker()

    for provider in set(providers.values()):
        if provider.updates or force_reload:
            provider.reload()

    return providers


@task
def generate_nginx_conf(role='www'):
    """
    Genereate nginx site config for web daemon

    :param str role: Name of role (directory) to generate config to
    """
    name = blueprint.get('project')
    socket = blueprint.get('web.socket', default='0.0.0.0:3030')
    host, _, port = socket.partition(':')
    if port:
        if len(env.hosts) > 1:
            # Multiple hosts -> Bind upstream to each host:port
            sockets = ['{}:{}'.format(host, port) for host in env.hosts]
        else:
            # Single host -> Bind upstream to unique configured socket
            sockets = [socket]
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
    web_provider = blueprint.get('web.provider')
    if web_provider and web_provider == 'uwsgi':
        template = 'nginx/uwsgi_site.conf'
    conf = blueprint.render_template(template, context)
    conf_dir = os.path.join(os.path.dirname(env['real_fabfile']), 'templates', role, 'nginx',
                            'sites-available')
    conf_path = os.path.join(conf_dir, '{}.conf'.format(name))

    if not os.path.exists(conf_dir):
        os.makedirs(conf_dir)

    with open(conf_path, 'w+') as f:
        f.write(conf)
