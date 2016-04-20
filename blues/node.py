"""
Node.js Blueprint
=================

**Fabric environment:**

.. code-block:: yaml

    blueprints:
      - blues.node

    settings:
      node:
        # version: latest    # Install latest node version
        packages:            # List of npm packages to install (Optional)
          # - coffee-script
          # - yuglify
          # - less

"""
import json
import os

from fabric.contrib import files
from fabric.context_managers import cd
from fabric.decorators import task

from refabric.api import info
from refabric.context_managers import sudo
from refabric.contrib import blueprints
from refabric.operations import run

from .application.project import git_repository_path, \
    sudo_project, project_name
from .util import maybe_managed

from . import debian

__all__ = ['setup', 'configure']


blueprint = blueprints.get(__name__)


@task
def setup():
    """
    Setup Nodejs
    """
    install()
    configure()


@task
def configure():
    """
    Install npm packages and, if bower is in the packages,
    install bower dependencies.
    """
    install_packages()
    install_dependencies()


def get_version():
    return blueprint.get('version')


def install(for_user=None):
    version = get_version()

    if version == 'latest':
        info('Installing latest node from tarball', )
        with sudo():
            install_node_build_deps()

        if for_user is not None:
            cm = sudo(user=for_user)
        else:
            cm = None

        with maybe_managed(cm):
            return install_latest()

    else:
        info('Installing node from apt')
        return install_deb()


def install_node_build_deps():
    info('Installing build tools')
    debian.apt_get_update()
    debian.apt_get('install', 'build-essential node-rimraf')


def install_latest():
    info('Installing latest node and NPM for {user}', user=run('whoami').stdout)

    common = [
        'set -x',
        'set -o verbose',
        'eval PREFIX=~/.local',
        'eval PROFILE=~/.bash_profile',
        'eval SRC=~/node-latest-install',
        'source $PROFILE',
    ]

    setup_env = [
        'echo \'export PATH=$HOME/.local/bin:$PATH\' >> $PROFILE',
        'echo \'export npm_config_userconfig=$HOME/.config/npmrc\' >> $PROFILE',
        'source $PROFILE',
        'mkdir $PREFIX || true',
        'mkdir $SRC || true'
    ]

    run(' && '.join(common + setup_env), shell=True)

    install_node_and_npm = [
        'cd $SRC',
        ('curl -z node-latest.tar.gz'
         ' -O http://nodejs.org/dist/node-latest.tar.gz'),
        'tar xz --strip-components=1 --file node-latest.tar.gz',
        './configure --prefix=$PREFIX',
        'make install',
        'curl -L https://www.npmjs.org/install.sh | sh'
    ]

    run(' && '.join(common + install_node_and_npm), shell=True)


def install_deb():
    with sudo():
        lbs_release = debian.lbs_release()

        # 12.04 ships with really old nodejs, TODO: 14.04?
        if lbs_release in ['10.04', '12.04']:
            info('Adding ppa...')
            debian.add_apt_ppa('chris-lea/node.js', src=True)

        info('Installing Node.js')
        debian.apt_get('install', 'nodejs')

        if lbs_release == '14.04':
            info('Installing NPM')
            debian.apt_get('install', 'npm')
            debian.ln('/usr/bin/nodejs', '/usr/bin/node')


def install_packages():
    packages = blueprint.get('packages', [])
    if packages:
        info('Installing Packages')
        npm('install', *packages)


def npm(command, *options):
    info('Running npm {}', command)
    with sudo():
        run('npm {} -g {}'.format(command, ' '.join(options)))


def install_dependencies(path=None, production=True, changed=True):
    """
    Install dependencies from "package.json" at path.

    :param path: Package path, current directory if None. [default: None]
    :param production:
        Boolean flag to toggle `--production` parameter for npm
    :param changed:
        Boolean flag or tuple of two commit sha to check if package.json and
        bower.json were changed.
    :return:
    """

    dependency_path_root = path or git_repository_path()

    has_file = lambda x: files.exists(os.path.join(dependency_path_root, x))
    has_package = has_file('package.json')
    has_bower = has_file('bower.json')

    with sudo_project(), cd(dependency_path_root):

        npm_changed = bower_changed = changed

        if isinstance(changed, tuple):  # i.e. commits: (from_sha, to_sha)
            changed = '{}..{}'.format(*changed)

            from blues import git

            if has_package:
                npm_changed = git.diff_stat(
                    git_repository_path(), changed, 'package.json')[0]

            if has_bower:
                bower_changed = git.diff_stat(
                    git_repository_path(), changed, 'bower.json')[0]

        if has_package and npm_changed:
            run('npm install' + (' --production' if production else ''))

        if has_bower and bower_changed:
            run('test -f bower.json && '
                'bower install --config.interactive=false')


def create_symlinks(npm_path='../node_modules',
                    bower_path='../bower_components',
                    bowerrc_path='.bowerrc',
                    clear=False):

    with cd(git_repository_path()):
        # get bower components dir from config file
        b = run('cat %s 2>/dev/null || true' % bowerrc_path) or '{}'
        b = json.loads(b).get('directory') or 'bower_components'

        for src, dst in [
            (npm_path, ''),
            (bower_path, b),
        ]:
            if src:
                src = os.path.abspath(os.path.join(git_repository_path(), src))
                if clear:
                    run('rm -rf {src} || true'.format(src=src))
                run('mkdir -p {src} && ln -sf {src} {dst}'.format(
                    src=src,
                    dst=dst,
                ), user=project_name())
