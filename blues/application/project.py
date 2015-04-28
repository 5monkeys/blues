import os
from contextlib import contextmanager

from refabric.context_managers import sudo
from refabric.contrib import blueprints

from .. import git

__all__ = [
    'app_root', 'project_home', 'git_root', 'use_virtualenv', 'virtualenv_path',
    'git_repository', 'git_repository_path', 'python_path', 'sudo_project',
    'requirements_txt', 'use_python',
]

blueprint = blueprints.get('blues.app')

use_python = lambda: blueprint.get('use_python', True)

use_virtualenv = lambda: blueprint.get('use_virtualenv', True) and use_python()

# /srv/app
app_root = lambda: blueprint.get('root_path') or '/srv/app'
# /srv/app/project
project_home = lambda: os.path.join(app_root(), blueprint.get('project'))
# /srv/app/project/src
git_root = lambda: os.path.join(project_home(),
                                'src')
# /srv/app/project/env
virtualenv_path = lambda: os.path.join(project_home(),
                                       'env')
# git repo dict
git_repository = lambda: git.parse_url(blueprint.get('git_url'),
                                       branch=blueprint.get('git_branch'))
# /srv/app/project/src/repo.git
git_repository_path = lambda: os.path.join(git_root(),
                                           git_repository()['name'])
# /srv/app/project/src/repo.git
python_path = lambda: os.path.join(git_repository_path(),
                                   blueprint.get('git_source', 'src'))
# /srv/app/project/src/repo.git/requirements.txt
requirements_txt = lambda: os.path.join(git_repository_path(),
                                        blueprint.get('requirements',
                                                      'requirements.txt'))
project_name = lambda: blueprint.get('project')


@contextmanager
def sudo_project():
    project_name = blueprint.get('project')
    with sudo(project_name):
        yield project_name
