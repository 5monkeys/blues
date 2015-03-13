import os

from fabric.context_managers import cd
from fabric.state import env
from fabric.utils import indent, abort
from blues.application.project import git_repository_path

from refabric.context_managers import sudo
from refabric.operations import run
from refabric.utils import info
from refabric.contrib import blueprints

from .providers import get_providers

from .. import debian
from .. import git
from .. import user
from .. import python
from .. import virtualenv

__all__ = [
    'install_project',
    'install_project_user',
    'install_project_structure',
    'install_system_dependencies',
    'install_virtualenv',
    'install_requirements',
    'install_or_update_source',
    'install_source',
    'update_source',
    'install_providers'
]


blueprint = blueprints.get('blues.app')


def install_project():
    create_app_root()
    install_project_user()
    install_project_structure()
    install_system_dependencies()
    install_or_update_source()


def create_app_root():
    from .project import app_root

    with sudo():
        # Create global apps root
        root_path = app_root()
        debian.mkdir(root_path, recursive=True)


def install_project_user():
    """
    Create project user and groups.
    Create user home dir.
    Disable ssh host checking.
    Create log dir.
    """
    from .project import project_home

    with sudo():
        info('Install application user')
        username = blueprint.get('project')
        home_path = project_home()

        # Setup groups for project user
        project_user_groups = ['app-data', 'www-data']
        for group in project_user_groups:
            debian.groupadd(group, gid_min=10000)

        # Get UID for project user
        user.create_system_user(username, groups=project_user_groups,
                                home=home_path)

        # Create application log path
        application_log_path = os.path.join('/var', 'log', username)
        debian.mkdir(application_log_path, group='app-data', mode=1775)

        # Configure ssh for github
        user.set_strict_host_checking(username, 'github.com')


def install_project_structure():
    """
    Create project directory structure
    """

    with sudo():
        info('Install application directory structure')
        project_name = blueprint.get('project')

        create_app_root()

        # Create static web paths
        static_base = blueprint.get('static_base', os.path.join('/srv/www/', project_name))
        static_path = os.path.join(static_base, 'static')
        media_path = os.path.join(static_base, 'media')
        debian.mkdir(static_path, group='www-data', mode=1775)
        debian.mkdir(media_path, group='www-data', mode=1775)


def install_system_dependencies():
    """
    Install system wide packages that application depends on.
    """
    with sudo():
        info('Install system dependencies')
        dependencies = blueprint.get('system_dependencies')
        if dependencies:
            debian.apt_get('update')
            debian.apt_get('install', *dependencies)


def install_virtualenv():
    """
    Create a project virtualenv.
    """
    from .project import sudo_project, virtualenv_path

    with sudo():
        virtualenv.install()

    with sudo_project():
        virtualenv.create(virtualenv_path())


def install_requirements(installation_file):
    """
    Pip install requirements in project virtualenv.
    """
    from .project import sudo_project, virtualenv_path, requirements_txt

    with sudo_project():
        path = virtualenv_path()

        info('Installing requirements from file {}', installation_file)

        with virtualenv.activate(path):
            if installation_file.endswith('.txt') or \
                    installation_file.endswith('.pip'):
                python.pip('install', '-r', installation_file)
            elif installation_file.endswith('.py'):
                with cd(git_repository_path()):
                    run('python {} develop'.format(installation_file))
            else:
                raise ValueError(
                    '"{}" is not a valid installation file'.format(
                        installation_file))


def install_or_update_source():
    """
    Try to install source, if already installed then update.
    """
    new_install = install_source()
    if not new_install:
        update_source()


def install_source():
    """
    Install git and clone application repository.

    :return: True, if repository got cloned
    """
    from .project import sudo_project, git_repository, git_root

    with sudo():
        git.install()

    with sudo_project() as project:
        path = git_root()
        debian.mkdir(path, owner=project, group=project)
        with cd(path):
            repository = git_repository()
            path, cloned = git.clone(repository['url'], branch=repository['branch'])
            if cloned is None:
                abort('Failed to install source, aborting!')

    return cloned


def update_source():
    """
    Update application repository with configured branch.

    :return: tuple(previous commit, current commit)
    """
    from .project import sudo_project, git_repository_path, git_repository

    with sudo_project():
        # Get current commit
        path = git_repository_path()
        previous_commit = git.get_commit(path, short=True)

        # Update source from git (reset)
        repository = git_repository()
        current_commit = git.reset(repository['branch'],
                                   repository_path=path,
                                   ignore=blueprint.get('git_force_ignore'))

        if current_commit is not None and current_commit != previous_commit:
            info(indent('(new version)'))
        else:
            info(indent('(same commit)'))

        return previous_commit, current_commit


def install_providers():
    """
    Install application providers on current host.
    """
    host = env.host_string
    providers = get_providers(host)
    for provider in providers.values():
        if hasattr(provider, 'manager') and provider.manager is not None:
            provider.manager.install()

        provider.install()
