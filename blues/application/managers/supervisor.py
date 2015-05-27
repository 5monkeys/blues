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

        template = self.get_provisioning_template(provider, program_name)

        self.updates.extend(
            self._upload_provider_template(
                template,
                name='{}.conf'.format(program_name),
                context=context))

        self.reload()

        return self.updates

    def _upload_provider_template(self, template, context, name):
        """
        Upload a template to the supervisor.d configuration dir.

        :param template: local template path
        :param context: template context
        :param name: remote configuration filename
        :return:
        """
        default_templates = supervisor.blueprint.get_default_template_root()

        destination = self.get_config_path()

        if name is not None:
            destination = os.path.join(destination, name)

        with settings(template_dirs=[default_templates]):
            return blueprint.upload(template, destination, context=context)

    def reload(self, program=None):
        supervisor.reload(program)
