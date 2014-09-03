import json
import os.path
from functools import partial

from fabric.context_managers import cd
from fabric.contrib import files
from fabric.decorators import task
from fabric.utils import warn, abort

from refabric.api import run, info
from refabric.context_managers import sudo, silent
from refabric.contrib import blueprints, debian

blueprint = blueprints.get(__name__)

logstash_root = '/etc/logstash'
conf_available_path = os.path.join(logstash_root, 'conf.templates')
conf_enabled_path = os.path.join(logstash_root, 'conf.d')
is_server = lambda: blueprint.get('server') is not None
is_client = lambda: blueprint.get('forwarder') is not None


@task
def setup():
    if is_server():
        install_server()
    if is_client():
        install_forwarder()
    upgrade()


@task
def upgrade():
    if is_server():
        upgrade_server()
    if is_client():
        upgrade_forwarder()


@task
def disable(conf, do_restart=True):
    disabled = False
    conf = conf if conf.endswith('.conf') else '{}.conf'.format(conf)
    with sudo(), cd(conf_enabled_path):
        if files.is_link(conf):
            info('Disabling conf: {}', conf)
            with silent():
                debian.rm(conf)
                disabled = True
            if do_restart:
                restart('server')
        else:
            warn('Invalid conf: {}'.format(conf))

    return disabled


@task
def enable(conf, weight, do_restart=True):
    enabled = False
    conf = conf if conf.endswith('.conf') else '{}.conf'.format(conf)

    with sudo():
        available_conf = os.path.join(conf_available_path, conf)
        if not files.exists(available_conf):
            warn('Invalid conf: {}'.format(conf))
        else:
            with cd(conf_enabled_path):
                weight = str(weight).zfill(2)
                conf = '{}-{}'.format(weight, conf)
                if not files.exists(conf):
                    info('Enabling conf: {}', conf)
                    with silent():
                        debian.ln(available_conf, conf)
                        enabled = True
                    if do_restart:
                        restart('server')

    return enabled


def install_server():
    with sudo():
        version = blueprint.get('server.version', '1.4')
        info('Adding apt repository for {} version {}', 'logstash', version)
        debian.add_apt_repository('http://packages.elasticsearch.org/logstash/{}/debian stable main'.format(version))

        info('Installing {} version {}', 'logstash', version)
        debian.apt_get('update')
        debian.apt_get('install', 'logstash')

        # Enable on boot
        debian.add_rc_service('logstash')

        # Create and download SSL cert
        create_server_ssl_cert()
        download_server_ssl_cert()


def create_server_ssl_cert():
    with sudo():
        info('Generating SSL certificate...')
        debian.mkdir('/etc/pki/tls/certs')
        debian.mkdir('/etc/pki/tls/private')
        with cd('/etc/pki/tls'):
            key = 'private/logstash-forwarder.key'
            crt = 'certs/logstash-forwarder.crt'
            run('openssl req -x509 -batch -nodes -days 3650 -newkey rsa:2048 -keyout {} -out {}'.format(key, crt))


def download_server_ssl_cert(destination='ssl/'):
    blueprint.download('/etc/pki/tls/certs/logstash-forwarder.crt', destination)


def configure_server(config, auto_disable_conf=True, **context):
    context.setdefault('use_ssl', True)
    context.setdefault('elasticsearch_host', '127.0.0.1')
    uploads = blueprint.upload('./server/', '/etc/logstash/', context)

    # Disable previously enabled conf not configured through config in settings
    changes = []
    if auto_disable_conf:
        with silent():
            enabled_conf_links = run('ls {}'.format(conf_enabled_path)).split()
        conf_prospects = ['{}-{}.conf'.format(str(weight).zfill(2), conf) for weight, conf in config.iteritems()]
        for link in enabled_conf_links:
            if link not in conf_prospects:
                changed = disable(link, do_restart=False)
                changes.append(changed)

    # Enable conf from settings
    for weight, conf in config.iteritems():
        changed = enable(conf, weight, do_restart=False)
        changes.append(changed)

    return bool(uploads or any(changes))


def upgrade_server():
    config = blueprint.get('server.config', {})
    auto_disable_conf = blueprint.get('server.auto_disable_conf', True)
    context = {
        'use_ssl': blueprint.get('use_ssl', True),
        'elasticsearch_host': blueprint.get('server.elasticsearch_host', '127.0.0.1')
    }

    changed = configure_server(config, auto_disable_conf=auto_disable_conf, **context)

    # Restart logstash if new templates or any conf has been enabled/disabled
    if changed:
        restart('server')


def install_forwarder():
    with sudo():
        info('Adding apt repository for {}', 'logstash forwarder')
        debian.add_apt_repository('http://packages.elasticsearch.org/logstashforwarder/debian stable main')

        info('Installing {}', 'logstash forwarder')
        debian.apt_get('update')
        debian.apt_get('install', 'logstash-forwarder')

        # Upload init script
        blueprint.upload('forwarder/init.d/logstash-forwarder', '/etc/init.d/')
        debian.chmod('/etc/init.d/logstash-forwarder', mode=755)

        # Enable on boot
        debian.add_rc_service('logstash-forwarder')


def upgrade_forwarder():
    files_json = json.dumps(blueprint.get('forwarder.files', []), indent=2).replace('\n', '\n  ')
    servers = ', '.join('"{}:5000"'.format(s) for s in blueprint.get('forwarder.servers', []))
    context = {
        'use_ssl': blueprint.get('use_ssl', True),
        'servers': servers,
        'files': files_json
    }
    uploads = blueprint.upload('forwarder/logstash-forwarder.conf', '/etc/logstash-forwarder', context=context)

    ssl_path = 'ssl/logstash-forwarder.crt'
    if not os.path.exists(blueprint.get_template_path(ssl_path)):
        download_server_ssl_cert(ssl_path)
    blueprint.upload('ssl/logstash-forwarder.crt', '/etc/pki/tls/certs/')

    if uploads:
        restart('forwarder')


def service(target=None, action=None):
    """
    Debian service dispatcher for logstash server and forwarder
    """
    if not target:
        abort('Missing logstash service target argument, start:<server|forwarder|both>')
    if target in ('server', 'both'):
        debian.service('logstash', action, check_status=False)
    if target in ('forwarder', 'both'):
        debian.service('logstash-forwarder', action, check_status=False)

start = task(partial(service, action='start'))
stop = task(partial(service, action='stop'))
restart = task(partial(service, action='restart'))
