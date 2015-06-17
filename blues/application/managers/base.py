import os
from fabric.state import env

from ..project import *

from ... import debian
from ...app import blueprint

from . import get_manager

from refabric.contrib import blueprints
from refabric.utils import info

blueprint = blueprints.get('blues.app')


class BaseManager(object):
    def __init__(self):
        self.updates = []
        self.project = blueprint.get('project')

    def install(self):
        """
        Install manager.

        :return:
        """
        raise NotImplementedError

    def get_context(self):
        context = {
            'current_host': env.host_string,
            'user': debian.get_user()
        }

        return context

    def get_provisioning_template(self, provider, program_name=None):
        """
        Find the provider's configuration file for this manager.

        If program name is set and <provider>/<manager>/<program_name>.conf
        exists, it will be returned. Otherwise
        <provider>/<manager>/<provider>.conf will be used.

        :param provider: The provider whose configuration we're looking for.
        :param program_name: Optional program name. May be used to avoid
        collisions, or because it looks pretty.
        :return: a path to a template
        """
        default_template = os.path.join(provider.name, self.name, provider.name)

        if program_name is not None:
            conf_name = program_name

            if not conf_name.endswith('.conf'):
                conf_name = '{}.conf'.format(conf_name)

            named_template = os.path.join(provider.name, self.name, conf_name)

            user_templates = blueprint.get_user_template_path()

            if os.path.isfile(os.path.join(user_templates, named_template)):
                info('Using local {} from {}', named_template, user_templates)
                return named_template

        return default_template

    def configure_provider(self, provider, context, program_name=None):
        """
        This method is called from providers in order to upload their
        run configuration to the manager.
        :param provider: The provider's instance
        :param context: Template context
        :param program_name: Optional program name, to avoid collisions if
        you have multiple instances of the same provider running under the
        same manager.
        :return:
        """
        raise NotImplementedError('managers usually need to implement a '
                                  'configure_provider method.')