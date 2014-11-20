import os

from fabric.context_managers import cd
from fabric.state import env
from fabric.utils import indent

from refabric.context_managers import sudo
from refabric.utils import info

from . import blueprint
from .project import *
from .providers import get_providers

from .. import debian
from .. import git
from .. import user
from .. import python
from .. import virtualenv


def install_project_user():
    """
    Create project user and groups.
    Create user home dir.
    Disable ssh host checking.
    """
    with sudo():
        info('Install application user')
        username = blueprint.get('project')
        home_path = project_home()

        # Get UID for project user
        user.create(username, home_path, groups=['app-data', 'www-data'])

        # Configure ssh for github
        user.set_strict_host_checking(username, 'github.com')


def install_project_structure():
    """
    Create project directory structure
    """
    with sudo():
        info('Install application directory structure')
        project_name = blueprint.get('project')

        # Create global apps root
        root_path = app_root()
        debian.mkdir(root_path)

        # Create static web paths
        static_base = os.path.join('/srv/www/', project_name)
        static_path = os.path.join(static_base, 'static')
        media_path = os.path.join(static_base, 'media')
        debian.mkdir(static_path, group='www-data', mode=1775)
        debian.mkdir(media_path, group='www-data', mode=1775)

        # Create application log path
        application_log_path = os.path.join('/var', 'log', project_name)
        debian.mkdir(application_log_path, group='app-data', mode=1775)


def install_system_dependencies():
    """
    Install system wide packages that application depends on.
    """
    with sudo():
        info('Install system dependencies')
        dependencies = blueprint.get('system_dependencies')
        if dependencies:
            debian.apt_get('install', *dependencies)


def install_virtualenv():
    """
    Create a project virtualenv.
    """
    with sudo():
        virtualenv.install()

    with sudo_project():
        virtualenv.create(virtualenv_path())


def install_requirements():
    """
    Pip install requirements in project virtualenv.
    """
    with sudo_project():
        info('Install requirements')
        path = virtualenv_path()
        requirements = requirements_txt()
        with virtualenv.activate(path):
            python.pip('install', '-r', requirements)


def install_source():
    """
    Install git and clone application repository.
    """
    with sudo():
        git.install()

    with sudo_project() as project:
        path = git_root()
        debian.mkdir(path, owner=project, group=project)
        with cd(path):
            repository = git_repository()
            git.clone(repository['url'], branch=repository['branch'])


def update_source():
    """
    Update application repository with configured branch.

    :return: tuple(previous commit, current commit)
    """
    with sudo_project():
        # Get current commit
        path = git_repository_path()
        previous_commit = git.get_commit(path, short=True)

        # Update source from git (reset)
        repository = git_repository()
        current_commit = git.reset(repository['branch'], repository_path=path)

        if current_commit != previous_commit:
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
        provider.install()
