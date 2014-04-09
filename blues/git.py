import os
from fabric.context_managers import cd
from fabric.contrib import files
from fabric.decorators import task
from refabric.context_managers import silent, sudo
from refabric.contrib import debian, blueprints
from refabric.operations import run
from refabric.utils import info

blueprint = blueprints.get(__name__)


def install():
    with sudo():
        debian.apt_get('install', 'git')


@task
def setup():
    install()
    upgrade()


@task
def upgrade():
    pass


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


def reset(branch, repository_path=None):
    if not repository_path:
        repository_path = debian.pwd()

    with cd(repository_path):
        name = repository_path.rsplit('/')[-1]
        info('Resetting git repository: {}@{}', name, branch)
        commands = [
            'git fetch origin',  # Fetch branches and tags
            'git reset --hard HEAD',  # Make hard reset to HEAD
            'git clean -fdx',  # Remove untracked files pyc, xxx~ etc
            'git checkout HEAD',  # Checkout HEAD
            'git reset refs/remotes/origin/{} --hard'.format(branch)  # Reset to branch
        ]
        with silent():
            output = run(' && '.join(commands))
            output = output.split(os.linesep)[-1].lstrip('HEAD is now at ')
            info('HEAD is now at: {}', output)
