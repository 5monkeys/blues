"""
wkhtmltopdf Blueprint

blueprints:
  - blues.wkhtmltopdf

"""
from fabric.decorators import task

from refabric.context_managers import sudo
from refabric.contrib import blueprints

from . import debian

__all__ = ['setup', 'configure']


blueprint = blueprints.get(__name__)


@task
def setup():
    """
    Install and configure wkhtmltopdf
    """
    install()
    configure()


def install():
    with sudo():
        packages = ['wkhtmltopdf', 'xvfb', 'xfonts-100dpi', 'xfonts-75dpi', 'xfonts-cyrillic']
        debian.apt_get('install', *packages)


@task
def configure():
    """
    Configure wkhtmltopdf
    """
    destination = '/usr/local/bin/wkhtmltopdf.sh'
    blueprint.upload('wkhtmltopdf.sh', destination)
    with sudo():
        debian.chmod(destination, '+x')
