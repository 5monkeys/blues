"""
PAM Environment Blueprint
==============

Updates section of ~/.pam_environment file for specified users defining
shell envs from the deploy config incl optional extra variables provided
in settings (which can override shell_env).

**Fabric environment:**

.. code-block:: yaml

    blueprints:
      - pam_env

    settings:
      pam_env:
        all:
          ALL_USERS_EXTRA_ENV_VAR: "some value"
        myuser:
          MYUSER_EXTRA_ENV_VAR: "some value"

"""
from fabric.decorators import task
from refabric.contrib import blueprints

__all__ = ['configure']


blueprint = blueprints.get(__name__)


@task
def configure():
    """
    Update .env file with environment variables
    """
    from blues.application.tasks import configure_providers
    from blues.application.project import project_home, project_name
    from fabric.state import env

    e = env['shell_env'].copy()
    e.update(blueprint.settings())
    escape = lambda v: str(v).replace('\\', '\\\\').replace('"', '\\"')
    e = map(lambda v: (v[0], escape(v[1])), sorted(e.items()))

    changed = blueprint.upload('./', project_home(), user=project_name(),
                               context={'shell_env': e})
    if changed:
        configure_providers(force_reload=True)
