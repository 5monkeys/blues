import os.path

from fabric.decorators import task
from fabric.operations import local, prompt
from fabric.state import env

from refabric.api import run, info
from refabric.context_managers import sudo
from refabric.contrib import blueprints, debian

blueprint = blueprints.get(__name__)


@task
def setup():
    install()
    upgrade()


def install():
    with sudo():
        info('Downloading kibana')
        version = blueprint.get('version', '3.1.0')
        tar_file = 'kibana-{}.tar.gz'.format(version)
        run('wget -P /tmp/ https://download.elasticsearch.org/kibana/kibana/{f}'.format(f=tar_file))

        # Extract and soft link kibana in web root
        web_root = '/srv/www/'
        debian.mkdir(web_root, mode=1775, owner='www-data', group='www-data')
        run('tar xzf /tmp/{f} -C {web_root}'.format(f=tar_file, web_root=web_root))
        src_root = os.path.join(web_root, 'kibana-{version}'.format(version=version))
        debian.chown(src_root, owner='www-data', group='www-data', recursive=True)
        debian.ln(src_root, '/srv/www/kibana')


@task
def upgrade():
    blueprint.upload('config.js', '/srv/www/kibana/')


@task
def generate_nginx_conf(role='www'):
    info('Generating kibana config to nginx@{}...'.format(role))
    context = {
        'domain': blueprint.get('domain', '_'),
        'elasticsearch_host': blueprint.get('elasticsearch_host', '127.0.0.1')
    }
    template = 'nginx/kibana.conf'
    conf = blueprint.render_template(template, context)
    pwd = os.path.dirname(env['real_fabfile'])
    conf_dir = os.path.join(pwd, 'templates', role, 'nginx', 'sites-available')
    conf_path = os.path.join(conf_dir, 'kibana.conf')

    if not os.path.exists(conf_dir):
        os.makedirs(conf_dir)

    with open(conf_path, 'w+') as f:
        f.write(conf)

    info('Select username and password...')
    passwd_dir = os.path.join(pwd, 'templates', role, 'nginx', 'conf.d')
    passwd_path = os.path.join(passwd_dir, 'kibana.htpasswd')
    if not os.path.exists(passwd_dir):
        os.makedirs(passwd_dir)
    username = prompt('Username:', default='kibana')
    local('htpasswd -c {filename} {username}'.format(filename=passwd_path,
                                                     username=username))
