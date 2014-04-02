import os
from fabric.context_managers import cd
from fabric.contrib import files
from fabric.decorators import task
from refabric.context_managers import silent
from refabric.contrib import debian
from refabric.operations import run
from refabric.state import blueprint_settings
from refabric.utils import info

settings = blueprint_settings(__name__)


def install():
    debian.apt_get('install', 'git')


@task
def upgrade():
    raise NotImplementedError


def clone(url, branch, repository_path=None):
    name = url.rsplit('/')[-1]

    if not repository_path:
        repository_path = os.path.join('.', name)

    if not files.exists(os.path.join(repository_path, '.git')):
        info('Cloning {}@{} into {}', url, branch, repository_path)
        cmd = 'git clone -b {branch} {remote} {name}'.format(branch=branch, remote=url, name=name)
        run(cmd)
    else:
        info('Git repository already cloned: {}', name)

    return repository_path


def reset(repository_path, branch):
    with silent(), cd(repository_path):
        name = repository_path.rsplit('/')[-1]
        info('Resetting git repository: {}@{}', name, branch)
        commands = [
            'git fetch origin',  # Fetch branches and tags
            'git reset --hard HEAD',  # Make hard reset to HEAD
            'git clean -fdx',  # Remove untracked files pyc, xxx~ etc
            'git checkout HEAD',  # Checkout HEAD
        ]
        run(' && '.join(commands))
        # Reset to branch
        output = run('git reset refs/remotes/origin/{} --hard'.format(branch))
        output = output.lstrip('HEAD is now at ')
        info('HEAD is now at: {}', output)

        # # Fetch branches and tags
        # run('git fetch origin')
        # # Make hard reset to HEAD
        # run('git reset --hard HEAD')
        # # Remove untracked files pyc, xxx~ etc
        # run('git clean -fdx')
        # # Checkout HEAD
        # run('git checkout HEAD')
        # # What is this?
        # output = run('git reset refs/remotes/origin/{} --hard'.format(branch))
