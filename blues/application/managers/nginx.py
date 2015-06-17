import os

from fabric.context_managers import settings
from refabric.context_managers import sudo
from refabric.contrib import blueprints

from .base import BaseManager

from ... import nginx

blueprint = blueprints.get('blues.app')


class NginxManager(BaseManager):
    name = 'nginx'

    def install(self):
        with sudo():
            nginx.install()

    def reload(self):
        with sudo():
            nginx.reload()

    def configure_provider(self, provider, context, program_name=None):
        if program_name is None:
            program_name = provider.name

        context.update({'program_name': program_name})

        destination = nginx.sites_available_path

        template = self.get_provisioning_template(provider, program_name)

        default_templates = nginx.blueprint.get_default_template_root()

        with settings(template_dirs=[default_templates]):
            uploads = blueprint.upload(
                template,
                os.path.join(destination,
                             '{}.conf'.format(program_name)),
                context=context)

        self.updates.extend(uploads)

        self.reload()

        with sudo():
            nginx.enable(program_name)

        return self.updates