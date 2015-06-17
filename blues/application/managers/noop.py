from .base import BaseManager

class NoopManager(BaseManager):
    name = 'noop'

    def install(self):
        pass

    def reload(self):
        pass

    def configure_provider(self, provider, context, program_name=None):
        pass