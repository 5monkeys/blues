import os

from fabric.state import env
from fabric.context_managers import settings

from .base import ManagedProvider
from ..managers.supervisor import SupervisorManager
from ..project import *

from ... import debian
from ...app import blueprint


class CeleryProvider(ManagedProvider):
    name = 'celery'
    default_manager = 'supervisor'

    def install(self):
        pass

    def configure_web(self):
        raise NotImplementedError('celery cannot be configured as a web '
                                  'provider')

    def get_context(self):
        context = super(CeleryProvider, self).get_context()
        context.update({
            'workers': blueprint.get('worker.workers', debian.nproc()),
        })

        # Override context defaults with blueprint settings
        context.update(blueprint.get('worker'))

        return context

    def reload(self):
        for program in self.get_programs():
            name, _, _ = program.partition('.')
            self.manager.reload(name)

    @staticmethod
    def get_programs():
        # Filter program extensions by host
        programs = ['celery.conf']
        extensions = blueprint.get('worker.celery.extensions')

        if isinstance(extensions, list):
            # Filter or bad values
            extensions = [extension for extension in extensions if extension]
            for extension in extensions:
                programs.append('{}.conf'.format(extension))
        elif isinstance(extensions, dict):
            for extension, extension_host in extensions.items():
                if extension_host in ('*', env.host_string):
                    programs.append('{}.conf'.format(extension))

        return programs

    def configure_worker(self):
        """
        Render and upload worker program(s) to projects Supervisor home dir.

        :return: Updated programs
        """
        return self.configure()

    def configure(self):
        context = self.get_context()

        for program in self.get_programs():
            template = os.path.join('supervisor', 'default', program)
            if not hasattr(self.manager, '_upload_provider_template'):
                raise Exception('the celery provider only works with the '
                                'supervisor manager as of now.')

            self.updates.extend(
                self.manager._upload_provider_template(
                    template,
                    context,
                    program))

        return self.updates
