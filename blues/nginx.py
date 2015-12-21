"""
Nginx Blueprint
===============

**Fabric environment:**

.. code-block:: yaml

    blueprints:
      - blues.nginx

    settings:
      nginx:
        source_version: 1.4.6-1ubuntu3.3  # Required if installed from source (see modules)
        sites:                            # List of sites/templates in `sites-available` folder to enable (Optional)
          - foo                           # Template name, with or without .conf extension
          - bar
        # auto_disable_sites: true  # Auto disable sites not specified in `sites` setting (Default: true)
        # modules:                  # If present, nginx will be built and installed from source with these modules
        #   - rtmp
        #   - vod

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
    if blueprint.get('modules'):
        install_from_source()
    else:
        with sudo():
            debian.apt_get('install', 'nginx', 'nginx-extras')


def install_from_source():
    from blues import debian

    with sudo():
        debian.apt_get_update()

        # Install dependencies
        packages = ('build-essential', 'libpcre3', 'libpcre3-dev',
                    'libssl-dev', 'dpkg-dev', 'git', 'software-properties-common')
        debian.apt_get('install', *packages)

        # Setup nginx source

        nginx_full_distro_version = blueprint.get('source_version')
        if not nginx_full_distro_version:
            raise TypeError('You are installing from nginx from source, please specify source_version')

        nginx_version, nginx_distro_version = nginx_full_distro_version.split('-')

        nginx_source_path = '/usr/src/nginx'
        nginx_source_version_path = os.path.join(nginx_source_path, 'nginx-{}'.format(nginx_version))
        nginx_source_module_path = os.path.join(nginx_source_version_path, 'debian/modules/')

        debian.mkdir(nginx_source_path)
        with cd(nginx_source_path):
            debian.apt_get('source', 'nginx={}'.format(nginx_full_distro_version))
            debian.apt_get('build-dep', '-y nginx={}'.format(nginx_full_distro_version))

        # Get wanted nginx modules
        nginx_modules = blueprint.get('modules')

        if 'rtmp' in nginx_modules:
            # Download nginx-rtmp module
            nginx_rtmp_version = '1.1.7'
            nginx_rtmp_module_path = os.path.join(nginx_source_module_path, 'nginx-rtmp-module')
            nginx_rtmp_module_version_path = os.path.join(nginx_source_module_path,
                                                          'nginx-rtmp-module-{}'.format(nginx_rtmp_version))

            archive_file = '{}.tar.gz'.format(nginx_rtmp_version)
            run('wget -P /tmp/ https://github.com/arut/nginx-rtmp-module/archive/v{f}'.format(
                f=archive_file))

            # Unpackage to nginx source directory
            run('tar xzf /tmp/v{f} -C {nginx_source_module_path}'.format(
                f=archive_file, nginx_source_module_path=nginx_source_module_path))

            # Set up nginx rtmp version symlink
            debian.ln(nginx_rtmp_module_version_path, nginx_rtmp_module_path)

            # Configure nginx dkpg, TODO: Do not add module if present in rules
            rtmp_module_string = '"s/^common_configure_flags := /common_configure_flags := \\\\\\\\\\\\\\\\\\n\\t\\t\\t--add-module=\\$\(MODULESDIR\)\/nginx-rtmp-module /g"'
            run('sed -ri {} {}'.format(rtmp_module_string,
                                       os.path.join(nginx_source_version_path, 'debian/rules')))

            # Install useful tools, like ffmpeg
            debian.add_apt_repository('ppa:mc3man/trusty-media', src=True)
            debian.apt_get_update()
            debian.apt_get('install', 'libfaac-dev', 'ffmpeg', 'zlib1g-dev', 'libjpeg8-dev')

        if 'vod' in nginx_modules:
            # Download nginx-rtmp module
            # nginx_vod_version = '2ac3bfeffab2fa1b46923236b7fd0ea15616a417'  # "Latest" git commit
            # nginx_vod_version = '88160cacd0d9789d84605425b78e3f494950529c'  # Git commit pre mms playready
            nginx_vod_version = 'master'
            nginx_vod_module_path = os.path.join(nginx_source_module_path, 'nginx-vod-module')
            nginx_vod_module_version_path = os.path.join(nginx_source_module_path,
                                                         'nginx-vod-module-{}'.format(nginx_vod_version))
            archive_file = '{}.tar.gz'.format(nginx_vod_version)

            debian.rm(nginx_vod_module_version_path, recursive=True)

            run('wget -O /tmp/{f} https://github.com/5monkeys/nginx-vod-module/archive/{f}'.format(
                f=archive_file))

            # Unpackage to nginx source directory
            run('tar xzf /tmp/{f} -C {nginx_source_module_path}'.format(
                f=archive_file, nginx_source_module_path=nginx_source_module_path))

            # Set up nginx rtmp version symlink
            debian.ln(nginx_vod_module_version_path, nginx_vod_module_path)

            # Configure nginx dkpg, TODO: Do not add module if present in rules
            vod_module_string = '"s/^common_configure_flags := /common_configure_flags := \\\\\\\\\\\\\\\\\\n\\t\\t\\t--add-module=\\$\(MODULESDIR\)\/nginx-vod-module /g"'
            run('sed -ri {} {}'.format(vod_module_string,
                                       os.path.join(nginx_source_version_path, 'debian/rules')))

        # Setup nginx
        with cd(nginx_source_version_path):
            run('dpkg-buildpackage -b')
        with cd(nginx_source_path):
            run('dpkg --install nginx-common_{nginx_full_distro_version}_all.deb nginx-extras_{nginx_full_distro_version}_amd64.deb'.format(
                nginx_full_distro_version=nginx_full_distro_version))


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
        sites = blueprint.get('sites') or []
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
