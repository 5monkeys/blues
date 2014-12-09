"""
Application Blueprint
=====================

**Fabric environment:**

.. code-block:: yaml

    blueprints:
      - blues.app

    settings:
      app:
        git_url: git@github.com:foo/bar.git[@branch]  # Git repository to clone
        # git_branch: master                          # Branch to clone, if not specified in `git_url` setting
        # git_source: ./                              # Relative path within repository added to python path (Default: src/)

        # requirements: requirements/live.txt         # Pip requirements file to install (Default: requirements.txt)
        # system_dependencies:                        # List of debian packages to install
        #   - build-essential  # gcc
        #   - zlib1g-dev       # PIL, png
        #   - libjpeg62-dev    # PIL, jpeg

        web:                                          # Enable web workers
          provider: uwsgi                             # Set web provider
          # module: foobar.wsgi                       # Set wsgi module (Default: django.core.handlers.wsgi:WSGIHandler())
          # hosts:                                    # Optional host list restricting web provider installation
          #   - 10.0.0.10
          #   - 10.0.0.11
          #   - 10.0.0.12

        worker:                                       # Enable async workers
          provider: supervisor                        # Set worker provider (uwsgi or supervisor)
          module: foobar.celery                       # Set worker module to load
          # extensions:                               # Optional Worker framework specific extension configuration
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

      # Do not forget to configure the providers properly
      # uwsgi:
      #   version: 1.3
      # supervisor:
      #   version: 3.1.3

"""
from .application.tasks import *
from .application.deploy import update_source
__all__ = ['setup', 'configure', 'deploy', 'reload', 'configure_providers', 'generate_nginx_conf']
