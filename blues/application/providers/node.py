from contextlib import contextmanager

from fabric.context_managers import prefix, cd

from refabric.context_managers import sudo
from refabric.contrib import blueprints
from refabric.operations import run

from blues.util import maybe_managed

from ... import node, debian

from ..project import sudo_project, project_home, git_repository_path,\
    static_base

from .base import ManagedProvider

blueprint = blueprints.get('blues.app')


@contextmanager
def bash_profile():
    """
    Fixes stuff that non-interactive shells don't do automatically.
    """
    with prefix('export HOME={}'.format(project_home())), \
            prefix('source {}/.bash_profile'.format(project_home())):
        yield


class NodeProvider(ManagedProvider):
    name = 'node'
    default_manager = 'nginx'

    def install(self):
        with sudo():
            node.install_node_build_deps()

        # fabric's sudo() does not set $HOME to the sudo user's home.
        with sudo_project(), prefix('export HOME={}'.format(project_home())), \
                bash_profile():
            node.install_latest()
            node.npm('install', 'gulp', 'bower')

        self.build()

    def install_requirements(self):
        with sudo_project(), bash_profile(), cd(git_repository_path()):
            install_package_dependencies()

    def reload(self):
        self.build()

    def build(self):
        # This is necessary since the app blueprint doesn't care about
        # package.json change detection and handling.
        self.install_requirements()

        with sudo_project(), cd(git_repository_path()), bash_profile(), \
                prefix('export STATIC_BASE={}'.format(static_base())):
            run('gulp build')
            debian.chgrp(static_base(), group='www-data', recursive=True)

    def configure_web(self):
        return self.configure()

    def configure(self):
        context = self.get_context()

        return self.manager.configure_provider(self,
                                               context,
                                               program_name=self.project)


def install_package_dependencies(path=None):
    """
    Install dependencies from "package.json" at path.

    :param path: Package path, current directory if None. [default: None]
    :return:
    """
    cd_cm = None
    if path is not None:
        cd_cm = cd(path)

    with maybe_managed(cd_cm):
        run('npm install --production')
        run('test -f bower.json && bower install')