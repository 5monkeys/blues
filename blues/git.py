import os

from fabric.context_managers import cd
from fabric.contrib import files
from fabric.decorators import task

from refabric.api import run, info
from refabric.context_managers import sudo, silent
from refabric.contrib import blueprints, debian

blueprint = blueprints.get(__name__)


def install():
    with sudo():
        debian.apt_get('install', 'git')


@task
def setup():
    install()


@task
def upgrade():
    raise NotImplementedError


def clone(url, branch=None, repository_path=None, **kwargs):
    print url, branch
    repository = parse_url(url, branch=branch)
    name = repository['name']
    branch = repository['branch']

    if not repository_path:
        repository_path = os.path.join('.', name)

    if not files.exists(os.path.join(repository_path, '.git')):
        info('Cloning {}@{} into {}', url, branch, repository_path)
        cmd = 'git clone -b {branch} {remote} {name}'.format(branch=branch, remote=url, name=name)
        run(cmd)
    else:
        info('Git repository already cloned: {}', name)

    return repository_path


def reset(branch, repository_path=None, **kwargs):
    if not repository_path:
        repository_path = debian.pwd()

    with cd(repository_path):
        name = os.path.basename(repository_path)
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


def parse_url(url, branch=None):
    egg = None

    if '@' in url.split(':', 1)[-1]:
        url, url_branch = url.rsplit('@', 1)

        if '#' in url_branch:
            url_branch, egg = url_branch.split('#', 1)

        if not branch:
            branch = url_branch

    repository_name = url.rsplit('/', 1)[-1]

    return {
        'url': url,
        'name': repository_name,
        'branch': branch,
        'egg': egg
    }
