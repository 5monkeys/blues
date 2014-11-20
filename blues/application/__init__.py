from refabric.contrib import blueprints
blueprint = blueprints.get(__name__)

from .tasks import *
__all__ = ['setup', 'upgrade', 'deploy', 'reload', 'upgrade_providers', 'generate_nginx_conf']
