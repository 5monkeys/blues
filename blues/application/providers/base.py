from fabric.state import env

from ..project import *

from ... import debian
from ...app import blueprint

from ..managers import get_manager


class BaseProvider(object):
    def __init__(self):
        self.updates = []
        self.project = blueprint.get('project')

    def install(self):
        """
        Install provider.
        """
        raise NotImplementedError

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
            'virtualenv': virtualenv_path(),
            'current_host': env.host_string,
        }

        context.update(get_project_info())

        owner = debian.get_user(self.project)
        context.update(owner)  # name, uid, gid, ...

        return context

    def configure_web(self):
        """
        Render and upload provider web config files.

        :return: Updated config files
        """
        raise NotImplementedError

    def configure_worker(self):
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


def get_project_info():
    from .. import project
    return {key: getattr(project, key)()  # Get and call the attribute
            for key in ['app_root',
                        'project_home',
                        'virtualenv_path',
                        'git_repository',
                        'git_repository_path',
                        'python_path',
                        'requirements_txt',
                        'project_name']}


class ManagedProvider(BaseProvider):
    def __init__(self, manager=None, *args, **kw):
        super(ManagedProvider, self).__init__(*args, **kw)

        if not hasattr(self, 'default_manager'):
            raise AttributeError('%s has no default_manager attribute.' %
                                 self.__class__)

        if manager is None:
            manager = self.default_manager

        Manager = get_manager(manager)

        self.manager = Manager()

    def provision(self):
        self.manager.configure_provider(self,
                                        self.get_context(),
                                        program_name=self.project)
