"""
wkhtmltopdf Blueprint

.. code-block:: yaml

    blueprints:
        - blues.wkhtmltopdf

    settings:
        wkhtmltopdf:
            # wkhtmltopdf_version: 0.12.2.1

"""
from fabric.decorators import task

from refabric.context_managers import sudo, settings
from refabric.contrib import blueprints
from refabric.operations import run

from . import debian

__all__ = ['setup', 'configure']


blueprint = blueprints.get(__name__)


@task
def setup():
    """
    Install and configure wkhtmltopdf
    """
    install()

def install():
    """
    Install wkhtmltox from the pkgs on sourceforge that are compiled with
    patched QT. This version doesn't need X/Xvfb to run.
    """
    # Can't be named version since it'll conflict with fabrics own version variable
    wkhtmltox_ver = blueprint.get('wkhtmltopdf_version', '0.12.2.1')
    wkhtmltox_pkg = 'wkhtmltox-{}_linux-{}-amd64.deb'.format(
        wkhtmltox_ver, debian.lbs_codename())
    wkhtmltox_url = 'http://downloads.sourceforge.net/project/wkhtmltopdf/{}/{}'.format(
        wkhtmltox_ver, wkhtmltox_pkg)
    run('curl --silent --location --show-error --remote-name "{}"'.format(
        wkhtmltox_url))
    with sudo():
        with settings(warn_only=True):
            run('dpkg -i {}'.format(wkhtmltox_pkg))
        debian.apt_get('--fix-broken', 'install')
        debian.rm(wkhtmltox_pkg)

@task
def configure():
    """
    Configure wkhtmltopdf
    """
    pass
