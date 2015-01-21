"""
Git Blueprint
=============

Installs git and contains useful git commands for other blueprints to use.

**Fabric environment:**

.. code-block:: yaml

    blueprints:
      - blues.git

"""
import os
import re

from fabric.context_managers import cd
from fabric.contrib import files
from fabric.decorators import task
from fabric.utils import warn

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
    """
    Clone repository and branch.

    :param url: Git url to clone
    :param branch: Branch to checkout
    :param repository_path: Destination
    :param kwargs: Not used but here for easier kwarg passing
    :return: (destination, got_cloned bool)
    """
    repository = parse_url(url, branch=branch)
    name = repository['name']
    branch = repository['branch']
    cloned = False

    if not repository_path:
        repository_path = os.path.join('.', name)

    if not files.exists(os.path.join(repository_path, '.git')):
        info('Cloning {}@{} into {}', url, branch, repository_path)
        with silent('warnings'):
            cmd = 'git clone -b {branch} {remote} {name}'.format(branch=branch, remote=url, name=name)
            output = run(cmd)
        if output.return_code != 0:
            warn('Failed to clone repository "{}", probably permission denied!'.format(name))
            cloned = None
        else:
            cloned = True
    else:
        info('Git repository already cloned: {}', name)

    return repository_path, cloned


def reset(branch, repository_path=None, **kwargs):
    """
    Fetch, reset, clean and checkout repository branch.

    :return: commit
    """
    commit = None

    if not repository_path:
        repository_path = debian.pwd()

    with cd(repository_path):
        name = os.path.basename(repository_path)
        info('Resetting git repository: {}@{}', name, branch)

        with silent('warnings'):
            commands = [
                'git fetch origin',  # Fetch branches and tags
                'git reset --hard HEAD',  # Make hard reset to HEAD
                'git clean -fdx',  # Remove untracked files pyc, xxx~ etc
                'git checkout HEAD',  # Checkout HEAD
                'git reset refs/remotes/origin/{} --hard'.format(branch)  # Reset to branch
            ]
            output = run(' && '.join(commands))

        if output.return_code != 0:
            warn('Failed to reset repository "{}", probably permission denied!'.format(name))
        else:
            output = output.split(os.linesep)[-1][len('HEAD is now at '):]
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

        # Example output (note leading space):
        #    719 files changed, 104452 insertions(+), 29309 deletions(-)
        #    1 file changed, 1 insertion(+)
        output = run('git diff --shortstat {} -- {}'.format(commit, path), pty=False)
        parts = output.strip().split(', ') if output else []
        changed, insertions, deletions = 0, 0, 0

        for part in parts:
            match = re.match(r'^\s*(\d+)\s+(.+)$', part)
            if not match:
                raise ValueError('no regex match for {!r} in {!r}'.format(part, output))
            n, label = match.groups()
            if label.endswith('(+)'):
                insertions = int(n)
            elif label.endswith('(-)'):
                deletions = int(n)
            elif label.endswith('changed'):
                changed = int(n)
            else:
                raise ValueError('unexpected git output')

        return changed, insertions, deletions


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
