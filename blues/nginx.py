"""
Nginx Blueprint
===============

**Fabric environment:**

.. code-block:: yaml

    blueprints:
      - blues.nginx

    settings:
      nginx:
        sites:                      # List of sites/templates in `sites-available` folder to enable (Optional)
          - foo                     # Template name, with or without .conf extension
          - bar
        # auto_disable_sites: true  # Auto disable sites not specified in `sites` setting (Default: true)

"""
import os

from fabric.context_managers import cd
from fabric.contrib import files
from fabric.decorators import task
from fabric.utils import warn

from refabric.api import run, info
from refabric.context_managers import sudo, silent
from refabric.contrib import blueprints

from . import debian

__all__ = ['start', 'stop', 'restart', 'reload', 'setup', 'configure',
           'enable', 'disable', 'tail']


blueprint = blueprints.get(__name__)

nginx_root = '/etc/nginx/'
sites_available_path = os.path.join(nginx_root, 'sites-available')
sites_enabled_path = os.path.join(nginx_root, 'sites-enabled')

start = debian.service_task('nginx', 'start')
stop = debian.service_task('nginx', 'stop')
restart = debian.service_task('nginx', 'restart')
reload = debian.service_task('nginx', 'reload')


@task
def setup():
    """
    Install and configure nginx
    """
    install()
    configure()
    restart()


def install():
    # Install package
    with sudo():
        debian.apt_get('install', 'nginx')
        debian.apt_get('install', 'nginx-extras')


@task
def configure():
    """
    Configure nginx and enable/disable sites
    """
    with sudo():
        # Upload templates
        context = {
            'num_cores': debian.nproc()
        }
        uploads = blueprint.upload('./', nginx_root, context)

        # Disable previously enabled sites not configured sites-enabled
        changes = []
        sites = blueprint.get('sites')
        auto_disable_sites = blueprint.get('auto_disable_sites', True)
        if auto_disable_sites:
            with silent():
                enabled_site_links = run('ls {}'.format(sites_enabled_path)).split()
            for link in enabled_site_links:
                link_name = os.path.splitext(link)[0]  # Without extension
                if link not in sites and link_name not in sites:
                    changed = disable(link, do_reload=False)
                    changes.append(changed)

        ### Enable sites from settings
        for site in sites:
            changed = enable(site, do_reload=False)
            changes.append(changed)

        ### Reload nginx if new templates or any site has been enabled/disabled
        if uploads or any(changes):
            reload()


@task
def disable(site, do_reload=True):
    """
    Disable site

    :param site: Site to disable
    :param do_reload: Reload nginx service
    :return: Got disabled?
    """
    disabled = False
    site = site if site.endswith('.conf') or site == 'default' else '{}.conf'.format(site)
    with sudo(), cd(sites_enabled_path):
        if files.is_link(site):
            info('Disabling site: {}', site)
            with silent():
                debian.rm(site)
                disabled = True
            if do_reload:
                reload()
        else:
            warn('Invalid site: {}'.format(site))

    return disabled


@task
def enable(site, do_reload=True):
    """
    Enable site

    :param site: Site to enable
    :param do_reload: Reload nginx service
    :return: Got enabled?
    """
    enabled = False

    if not (site.endswith('.conf') or site == 'default'):
        site = '{}.conf'.format(site)

    with sudo():
        available_site = os.path.join(sites_available_path, site)
        if not files.exists(available_site):
            warn('Invalid site: {}'.format(site))
        else:
            with cd(sites_enabled_path):
                if not files.exists(site):
                    info('Enabling site: {}', site)
                    with silent():
                        debian.ln(available_site, site)
                        enabled = True
                    if do_reload:
                        reload()

    return enabled


@task
def tail(log_name='error'):
    log_dir = '/var/log/nginx'
    run('tail -f {}'.format(
        os.path.join(log_dir,
                     '{}.log'.format(log_name))))
