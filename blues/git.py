import os
import re

from fabric.context_managers import cd
from fabric.contrib import files
from fabric.decorators import task

from refabric.api import run, info
from refabric.context_managers import sudo, silent
from refabric.contrib import blueprints

from . import debian

__all__ = ['setup']


blueprint = blueprints.get(__name__)


@task
def setup():
    """
    Install Git
    """
    install()


def install():
    with sudo():
        info('Installing: {}', 'Git')
        debian.apt_get('install', 'git')


def clone(url, branch=None, repository_path=None, **kwargs):
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
    """
    Fetch, reset, clean and checkout repository branch.

    :return: commit
    """
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
            commit = output.split()[0]
            info('HEAD is now at: {}', output)

    return commit


def get_commit(repository_path=None, short=False):
    """
    Get current checked out commit for cloned repository path.

    :param repository_path: Repository path
    :param short: Format git commit hash in short (7) format
    :return: Commit hash
    """
    if not repository_path:
        repository_path = debian.pwd()

    with cd(repository_path), silent():
        output = run('git rev-parse HEAD')
        commit = output.strip()
        if short:
            commit = commit[:7]

    return commit


def diff_stat(repository_path=None, commit='HEAD^', path=None):
    """
    Get diff stats for path.

    :param repository_path: Repository path
    :param commit: Commit to diff against, ex 12345..67890
    :param path: Path or file to diff
    :return: tuple(num files changed, num insertions, num deletions)
    """
    if not repository_path:
        repository_path = debian.pwd()

    with cd(repository_path), silent():
        output = run('git diff --shortstat {} {}'.format(commit, path), pty=False)

        # 719 files changed, 104452 insertions(+), 29309 deletions(-)
        pattern = '.*(\d+) .+, (\d+) .+, (\d+) .+'
        match = re.match(pattern, output)

        if match:
            stats = tuple(int(s) for s in match.groups())
        else:
            stats = 0, 0, 0

        return stats


def current_tag(repository_path=None):
    """
    Get most recent tag
    :param repository_path: Repository path
    :return: The most recent tag
    """
    if not repository_path:
        repository_path = debian.pwd()
    with cd(repository_path), silent():
        output = run('git describe --long --tags --dirty --always', pty=False)

        # 20141114.1-306-g72354ae-dirty
        return output.strip().rsplit('-', 2)[0]


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
