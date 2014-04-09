from functools import partial
import os
from fabric.context_managers import cd
from fabric.contrib import files
from fabric.decorators import task
from fabric.utils import indent, warn
from refabric.context_managers import sudo, silent
from refabric.contrib import debian, blueprints
from refabric.operations import run
from refabric.utils import info

blueprint = blueprints.get(__name__)

nginx_root = '/etc/nginx'
sites_available_path = os.path.join(nginx_root, 'sites-available')
sites_enabled_path = os.path.join(nginx_root, 'sites-enabled')

start = task(partial(debian.service, 'nginx', 'start', check_status=False))
stop = task(partial(debian.service, 'nginx', 'stop', check_status=False))
restart = task(partial(debian.service, 'nginx', 'restart', check_status=False))
reload = task(partial(debian.service, 'nginx', 'reload', check_status=False))


@task
def setup():
    install()
    upgrade()
    restart()


def install():
    # Install package
    with sudo():
        debian.apt_get('install', 'nginx')
        debian.apt_get('install', 'nginx-extras')


@task
def upgrade():
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
    enabled = False
    site = site if site.endswith('.conf') or site == 'default' else '{}.conf'.format(site)

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
