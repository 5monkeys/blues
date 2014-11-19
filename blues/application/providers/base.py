from blues import debian

from .. import blueprint
from ..project import *


class BaseProvider(object):

    def __init__(self):
        self.updates = []
        self.project = blueprint.get('project')

    def get_config_path(self):
        """
        Get or create remote provider config home dir.

        :return: Remote config path
        """
        raise NotImplementedError

    def get_context(self):
        """
        Build Jinja2 context for provider config templates.

        :return: context dict
        """
        context = {
            'chdir': python_path(),
            'virtualenv': virtualenv_path()
        }

        owner = debian.get_user(self.project)
        context.update(owner)  # name, uid, gid, ...

        return context

    def upload_web_config(self):
        """
        Render and upload provider web config files.

        :return: Updated config files
        """
        raise NotImplementedError

    def upload_worker_config(self):
        """
        Render and upload provider worker config files.

        :return: Updated config files
        """
        raise NotImplementedError

    def reload(self):
        """
        Reload provider configuration
        """
        pass
