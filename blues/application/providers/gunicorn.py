import os

from refabric.context_managers import sudo
from refabric.utils import info
from refabric.utils.socket import format_socket

from ..project import sudo_project, virtualenv_path

from ... import debian, python, virtualenv
from ...app import blueprint

from .base import ManagedProvider


class GunicornProvider(ManagedProvider):
    name = 'gunicorn'
    default_manager = 'supervisor'

    def install(self):
        with sudo_project(), virtualenv.activate(virtualenv_path()):
            python.pip('install', 'gunicorn')

    def reload(self):
        return self.manager.reload(self.project)

    def get_context(self):
        context = super(GunicornProvider, self).get_context()
        socket_string = blueprint.get('web.socket')

        if socket_string:
            socket_string = format_socket(socket_string)

        bp = {
            'socket': socket_string,
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
