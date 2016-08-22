"""
Let's encrypt Blueprint
===============
**Prerequisites:**
Webserver need to be configured to serve acme-challenge requests for requested domains

Example:
.. code-block:: nginx
    location ^~ /.well-known/acme-challenge/ {
        default_type "text/plain";
        root /srv/www/letsencrypt;
    }

    location = /.well-known/acme-challenge/ {
        return 404;
    }

**Fabric environment:**

.. code-block:: yaml

    blueprints:
      - blues.letsencrypt

    settings:
      letsencrypt:
        domains:                             # Domains to request certificates for
          - www.example.com
          - example.com

        # certbot_path: /opt/certbot/        # Location to install certbot-auto script
        # webroot_path: /srv/www/letsencrypt # Location from where acme-challenge requests are served

"""


from fabric.decorators import task
from fabric.context_managers import cd
from fabric.utils import warn

from refabric.context_managers import sudo
from refabric.contrib import blueprints
from refabric.operations import run

from . import debian

blueprint = blueprints.get(__name__)
certbot_path = blueprint.get('certbot_path', '/opt/certbot/')
webroot_path = blueprint.get('webroot_path', '/srv/www/letsencrypt')
script_path = certbot_path + 'certbot-auto'


@task
def setup():
    with sudo():
        debian.mkdir(certbot_path)
        debian.mkdir(webroot_path)
    with cd(certbot_path):
        run('wget -O {} https://dl.eff.org/certbot-auto'.format(script_path))
        run('chmod a+x certbot-auto')
        configure()


@task
def configure():
    domains = blueprint.get('domains')
    if not domains:
        warn('No domains specified for letsencrypt')
        return

    domains_command = ' -d '.join(domains)
    run(script_path + ' certonly --webroot -w {webroot} -d {domains}'.format(
        webroot=webroot_path, domains=domains_command))


@task
def renew():
    with sudo():
        run(script_path + ' renew')
