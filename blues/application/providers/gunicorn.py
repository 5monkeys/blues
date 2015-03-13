import os
from urlparse import urlparse
from blues import python, virtualenv
from blues.application.project import sudo_project, project_home, \
    virtualenv_path
from refabric.context_managers import sudo

from ... import debian
from ...app import blueprint

from .base import ManagedProvider
from refabric.utils import info


class GunicornProvider(ManagedProvider):
    name = 'gunicorn'
    default_manager = 'supervisor'

    def install(self):
        with sudo_project(), virtualenv.activate(virtualenv_path()):
            python.pip('install', 'gunicorn')

        self.manager.install()

        self.create_socket()

    def create_socket(self):
        socket = blueprint.get('web.socket')

        parts = urlparse(socket)

        if not parts.path:
            path = socket
        else:
            path = parts.path

        if len(path.split('/')) < 2:
            raise ValueError('socket cannot be placed in /.')

        info('Creating socket for gunicorn: %s' % path)

        with sudo():
            debian.mkdir(os.path.dirname(path))
            debian.chown(os.path.dirname(path), self.project)

    def get_context(self):
        context = super(GunicornProvider, self).get_context()
        socket = blueprint.get('web.socket')

        host, _, port = socket.partition(':')

        if not port:
            socket = 'unix://{}'.format(socket)

        bp = {
            'socket': socket,
            'workers': blueprint.get('web.workers', debian.nproc() * 2),
            'module': blueprint.get('web.module'),
        }

        context.update(bp)

        return context

    def configure(self):
        context = self.get_context()

        self.manager.configure_provider(self,
                                        context,
                                        program_name=self.project)

    def configure_web(self):
        return self.configure()