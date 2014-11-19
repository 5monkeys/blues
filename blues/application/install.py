import os

from fabric.context_managers import cd
from fabric.utils import indent

from refabric.context_managers import sudo
from refabric.utils import info

from . import blueprint
from .project import *
from .. import debian
from .. import git
from .. import user
from .. import python
from .. import virtualenv


def install():
    with sudo():
        project_name = blueprint.get('project')

        # Create global paths
        root_path = app_root()
        debian.mkdir(root_path)

        # Create project user
        install_project_user()

        # Create static web paths
        static_base = os.path.join('/srv/www/', project_name)
        static_path = os.path.join(static_base, 'static')
        media_path = os.path.join(static_base, 'media')
        debian.mkdir(static_path, group='www-data', mode=1775)
        debian.mkdir(media_path, group='www-data', mode=1775)

        # Create application log path
        application_log_path = os.path.join('/var', 'log', project_name)
        debian.mkdir(application_log_path, group='app-data', mode=1775)

        # Install system-dependencies
        install_system_dependencies()

        # Clone repository
        install_git()

        # Create virtualenv
        install_virtualenv()


def install_project_user():
    username = blueprint.get('project')
    home_path = project_home()

    # Get UID for project user
    user.create(username, home_path, groups=['app-data', 'www-data'])
    # Upload deploy keys for project user
    user.set_strict_host_checking(username, 'github.com')


def install_system_dependencies():
    django_dependencies = blueprint.get('system_dependencies')
    if django_dependencies:
        debian.apt_get('install', *django_dependencies)


def install_virtualenv():
    username = blueprint.get('project')
    virtualenv.install()
    with sudo(username):
        virtualenv.create(virtualenv_path())


def install_requirements():
    with sudo_project():
        path = virtualenv_path()
        pip_log_path = os.path.join(project_home(), '.pip', 'pip.log')
        with virtualenv.activate(path):
            python.pip('install', '-r {} --log={}'.format(requirements_txt(), pip_log_path))


def install_git():
    git.install()

    with sudo_project() as project:
        path = git_root()
        debian.mkdir(path, owner=project, group=project)
        with cd(path):
            repository = git_repository()
            git.clone(repository['url'], branch=repository['branch'])


def update_git():
    """
    Update git repository with configured branch.

    :return: tuple(previous commit, current commit)
    """
    with sudo_project():
        path = git_repository_path()

        previous_commit = git.get_commit(path, short=True)

        repository = git_repository()
        current_commit = git.reset(repository['branch'], repository_path=path)

        if current_commit != previous_commit:
            info(indent('(new version)'))
        else:
            info(indent('(same commit)'))

        return previous_commit, current_commit
