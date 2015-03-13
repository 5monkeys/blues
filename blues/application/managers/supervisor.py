import os

from fabric.context_managers import settings

from refabric.contrib import blueprints

from .base import BaseManager
from ..project import *

from ... import debian
from ... import supervisor

blueprint = blueprints.get('blues.app')


class SupervisorManager(BaseManager):
    name = 'supervisor'

    def install(self):
        """
        Install system wide Supervisor and upstart service.
        """
        supervisor.setup()

    def get_config_path(self):
        """
        Get or create Supervisor project programs home dir.

        :return: Remote config path
        """
        # Join config path and make sure that it ends with a slash
        destination = os.path.join(project_home(), 'supervisor.d', '')
        debian.mkdir(destination)
        return destination

    def configure_provider(self, provider, context, program_name=None):
        if program_name is None:
            program_name = provider.name

        context.update({'program_name': program_name})

        destination = self.get_config_path()
        template = self.get_provisioning_template(provider, program_name)
        default_templates = supervisor.blueprint.get_default_template_root()

        with settings(template_dirs=[default_templates]):
            uploads = blueprint.upload(
                template,
                os.path.join(destination,
                             '{}.conf'.format(program_name)),
                context=context)

        self.updates.extend(uploads)

        self.reload()

        return self.updates

    def reload(self, program=None):
        supervisor.reload(program)
