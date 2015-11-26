# coding=utf-8

import os

from fabric.context_managers import settings
from fabric.decorators import task
from fabric.state import env
from fabric.utils import indent, abort
from blues.application.deploy import maybe_install_requirements

from refabric.utils import info
from refabric.contrib import blueprints


from .. import git
from .. import slack

blueprint = blueprints.get('blues.app')

__all__ = []


def get_providers(*args, **kw):
    from .providers import get_providers as real
    return real(*args, **kw)


@task
def setup():
    """
    Install project user, structure, env, source, dependencies and providers
    """
    from .deploy import install_project, install_virtualenv, \
        install_requirements, install_providers
    from .project import requirements_txt, use_virtualenv

    install_project()

    if use_virtualenv():
        install_virtualenv()
        install_requirements(requirements_txt())

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
def deploy(auto_reload=True, force=False, update_pip=False):
    """
    Reset source to configured branch and install requirements, if needed

    :param bool auto_reload: Reload application providers if source has changed
    :param bool force: Force install of requirements
    :return bool: Source code has changed?
    """
    from .deploy import update_source
    from .project import use_virtualenv

    # Reset git repo
    previous_commit, current_commit = update_source()
    code_changed = current_commit is not None and \
                   previous_commit != current_commit

    if code_changed or force:
        # Install python dependencies
        if use_virtualenv():
            maybe_install_requirements(previous_commit, current_commit, force,
                                       update_pip=update_pip)

        # Reload providers
        if auto_reload:
            reload()

    return (previous_commit, current_commit) if code_changed else False


@task
def install_requirements():
    from .deploy import install_requirements
    from .project import use_virtualenv

    if use_virtualenv():
        install_requirements()
    else:
        abort('Cannot install requirements without virtualenv')


@task
def deployed():
    """
    Show deployed and last origin commit
    """
    from .project import sudo_project, git_repository_path

    with sudo_project():
        repository_path = git_repository_path()
        git.fetch(repository_path)

        head_commit, head_message = git.log(repository_path)[0]
        origin_commit, origin_message = git.log(repository_path,
                                                commit='origin')[0]

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
    from .project import sudo_project

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

    template = blueprint.get('web.nginx_conf')

    if template is None:
        template = 'nginx/site.conf'
    else:
        template = 'nginx/{}.conf'.format(template)

    web_provider = blueprint.get('web.provider')
    if web_provider and web_provider == 'uwsgi':
        template = 'nginx/uwsgi_site.conf'

    with settings(template_dirs=['templates']):
        conf = blueprint.render_template(template, context)
        conf_dir = os.path.join(
            os.path.dirname(env['real_fabfile']),
            'templates',
            role,
            'nginx',
            'sites-available')
        conf_path = os.path.join(conf_dir, '{}.conf'.format(name))

    if not os.path.exists(conf_dir):
        os.makedirs(conf_dir)

    with open(conf_path, 'w+') as f:
        f.write(conf)


def get_github_owner():
    from .project import git_repository
    from ..git import parse_url

    url = git_repository().get('url', '')
    if not url.startswith('git@github.com:'):
        return None

    return parse_url(url)['gh_owner']


def notify_deploy_start(role=None, notifier=slack.notify, quiet=False):
    from .project import project_name

    msg = '`{deployer}` started deploying '
    if role:
        msg += '`{project}@{state}:{role}` '
    else:
        msg += '`{project}@{state}` '

    msg += 'to `{user}@{host}`'

    msg = msg.format(
        deployer=git.get_local_commiter(),
        project=project_name(),
        state=env.get('state', 'unknown'),
        role=role,
        user=env['user'],
        host=env['host_string'],
    )

    if notifier:
        notifier(msg, quiet=quiet)

    return msg


def notify_deploy(role=None, commits=None, notifier=slack.notify, quiet=False):
    from .project import project_name, git_repository_path

    msg = '`{deployer}` deployed '
    if role:
        msg += '`{project}@{state}:{role}` '
    else:
        msg += '`{project}@{state}` '

    owner = get_github_owner()
    if owner:
        if commits:
            msg += '`<https://github.com/{owner}/{project}/compare/{from}...{to}|{from}→{to}>` '
        else:
            msg += '`<https://github.com/{owner}/{project}/commit/{commit}|{commit}>` '
    else:
        if commits:
            msg += '`{from}→{to}` '
        else:
            msg += '`{commit}` '

    msg += 'to `{user}@{host}`'

    from_commit, to_commit = commits or (None, None)
    commit = commits or git.get_commit(repository_path=git_repository_path(), short=True)
    variables = {
        'deployer': git.get_local_commiter(),
        'project': project_name(),
        'state': env.get('state', 'unknown'),
        'role': role,
        'owner': owner,
        'from': from_commit,
        'to': to_commit,
        'commit': commit,
        'user': env['user'],
        'host': env['host_string'],
    }

    notifier(msg.format(**variables), quiet=quiet)
