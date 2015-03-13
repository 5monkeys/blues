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

    def configure_web(self):
        raise NotImplementedError('celery cannot be configured as a web '
                                  'provider')

    def configure_worker(self):
        """
        Render and upload worker program(s) to projects Supervisor home dir.

        :return: Updated programs
        """
        from blues import supervisor

        destination = self.get_config_path()
        context = super(SupervisorManager, self).get_context()
        context.update({
            'workers': blueprint.get('worker.workers', debian.nproc()),
        })

        # Override context defaults with blueprint settings
        context.update(blueprint.get('worker'))

        # Filter program extensions by host
        programs = ['celery.conf']
        extensions = blueprint.get('worker.celery.extensions')
        if isinstance(extensions, list):
            # Filter of bad values
            extensions = [extension for extension in extensions if extension]
            for extension in extensions:
                programs.append('{}.conf'.format(extension))
        elif isinstance(extensions, dict):
            for extension, extension_host in extensions.items():
                if extension_host in ('*', env.host_string):
                    programs.append('{}.conf'.format(extension))

        # Upload programs
        for program in programs:
            template = os.path.join('supervisor', 'default', program)
            default_templates = supervisor.blueprint.get_default_template_root()
            with settings(template_dirs=[default_templates]):
                uploads = blueprint.upload(template, destination, context=context)
            self.updates.extend(uploads)

        return self.updates

    def reload(self):
        from blues import supervisor
        supervisor.reload()
