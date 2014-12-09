import os
from contextlib import contextmanager

from refabric.context_managers import sudo

from .. import git
from ..app import blueprint

__all__ = [
    'app_root', 'project_home', 'git_root', 'virtualenv_path', 'git_repository',
    'git_repository_path', 'python_path', 'sudo_project', 'requirements_txt'
]


app_root = lambda: blueprint.get('root_path') or '/srv/app'  # /srv/app
project_home = lambda: os.path.join(app_root(), blueprint.get('project'))  # /srv/app/project
git_root = lambda: os.path.join(project_home(), 'src')  # /srv/app/project/src
virtualenv_path = lambda: os.path.join(project_home(), 'env')  # /srv/app/project/env
git_repository = lambda: git.parse_url(blueprint.get('git_url'), branch=blueprint.get('git_branch'))  # git repo dict
git_repository_path = lambda: os.path.join(git_root(), git_repository()['name'])  # /srv/app/project/src/repo.git
python_path = lambda: os.path.join(git_repository_path(), blueprint.get('git_source', 'src'))  # /srv/app/project/src/repo.git
requirements_txt = lambda: os.path.join(git_repository_path(), blueprint.get('requirements', 'requirements.txt'))  # /srv/app/project/src/repo.git/requirements.txt


@contextmanager
def sudo_project():
    project_name = blueprint.get('project')
    with sudo(project_name):
        yield project_name
