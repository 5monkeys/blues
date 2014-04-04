from fabric.decorators import task
from refabric.contrib import debian, blueprints
from refabric.utils import info

blueprint = blueprints.get(__name__)


@task
def install():
    if debian.command_exists('nginx'):
        info('Already installed: {}', 'nginx')
        # return

    # # Install package
    # info('Installing: {}', 'nginx')
    # debian.apt_get('install', 'nginx')

    # Upload templates
    nginx_root = '/etc/nginx'
    # upload(templates, nginx_root, context=settings())
    from fabric.state import env
    from pprint import pprint
    pprint(env)

def site_disable(site):
    pass


def site_enable(site):
    pass
