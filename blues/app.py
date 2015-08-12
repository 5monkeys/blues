"""
Application Blueprint
=====================

**Fabric environment:**

.. code-block:: yaml

    blueprints:
      - blues.app

    settings:
      app:
        project: foobar                               # Name of the application, used as username, home, etc.
        git_url: git@github.com:foo/bar.git[@branch]  # Git repository to clone
        # git_branch: master                          # Branch to clone, if not specified in `git_url` setting
        # git_source: ./                              # Relative path within repository added to python path (Default: src/)
        # Do not reset these paths even if they are git-ignored
        # git_force_ignore:
        #  - /node_modules
        #  - /bower_components

        # use_python: false                           # Enable python support, required for virtualenv (Default: true)
        # use_virtualenv: false                       # Enable virtualenv and pip requirements, unless `use_python` is false (Default: true)
        # requirements: requirements/live.txt         # Pip requirements file to install (Default: requirements.txt)
        # system_dependencies:                        # List of debian packages to install
        #   - build-essential  # gcc
        #   - libmemcached-dev # memcached
        #   - python-dev       # postgres, psycopg2
        #   - libpq-dev        # postgres, psycopg2
        #   - zlib1g-dev       # PIL, png
        #   - libjpeg62-dev    # PIL, jpeg
        #   - libxml2-dev      # lxml
        #   - libxslt-dev      # lxml

        web:                                          # Enable web workers
          provider: uwsgi                             # Set web provider
          # module: foobar.wsgi                       # Set wsgi module (Default: django.core.handlers.wsgi:WSGIHandler())
          # socket: 127.0.0.1:3031                    # Set vassal socket (Default: 0.0.0.0:3030)
          # hosts:                                    # Optional host list restricting web provider installation
          #   - 10.0.0.10
          #   - 10.0.0.11
          #   - 10.0.0.12

        worker:                                       # Configure worker process
          # Set worker provider (uwsgi or supervisor)
          provider: celery:supervisor
          module: foobar.celery                       # Set worker module to load
          # extensions:                               # Optional Worker framework specific extension configuration [dict|list]
          #   - beat
          #   - flower
          #   (OR)
          #   beat: 10.0.0.12                         # Celery: Restrict beat service to specific host
          #   flower: 10.0.0.12                       # Celery: Restrict flower service to specific host
          # hosts:                                    # Optional host list restricting worker provider installation
          #   - 10.0.0.10
          #   - 10.0.0.11
          #   - 10.0.0.12
          # queues:                                   # Optional queue definitions
          #   index:                                  # Queue name
          #     workers: 2                            # Number of queue workers
                # hosts:                              # Optional host list restriction for queue
                #   - 10.0.0.11

      # Do not forget to configure the dependencies properly
      # uwsgi:
      #   version: 2.0.10
      # supervisor:
      #   version: 3.1.3
      # python:
      #   version: 3

"""
from refabric.contrib import blueprints
blueprint = blueprints.get(__name__)

from .application.tasks import setup, configure, deploy, deployed, start, stop,\
    reload, configure_providers, generate_nginx_conf, notify_deploy, \
    install_requirements, notify_deploy_start

from .application.deploy import update_source

__all__ = ['setup', 'configure', 'deploy', 'deployed', 'start', 'stop',
           'reload', 'configure_providers', 'generate_nginx_conf', 'install_requirements']
