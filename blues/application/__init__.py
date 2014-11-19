from refabric.contrib import blueprints

blueprint = blueprints.get(__name__)

from .tasks import *

__all__ = ['setup', 'upgrade', 'upgrade_providers', 'generate_nginx_conf']
