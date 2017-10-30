"""
Samba Blueprint
===================

**Fabric environment:**

.. code-block:: yaml

    blueprints:
      - blues.samba

    settings:
      samba:
        workgroup: WORKGROUP          # default: WORKGROUP

        shares:
          NAME:
            some_samba_option: value  # underscores in keys are replaced with space
            boolean_option: true      # value resolves to 'yes'
            boolean_option: false     # value resolves to 'no'
            some_samba_list_option:   # lists becomes space separated
              - value
              - value2
"""

from fabric.decorators import task
from refabric.context_managers import sudo
from refabric.contrib import blueprints

from . import debian

blueprint = blueprints.get(__name__)

start = debian.service_task('samba', 'start')
stop = debian.service_task('samba', 'stop')
restart = debian.service_task('samba', 'restart')
status = debian.service_task('samba', 'status')


def sambafy_options(options):
    def samba_value(value):
        if isinstance(value, list):
            return ' '.join(value)
        elif isinstance(value, bool):
            return {True: 'yes', False: 'no'}[value]

        return value

    return {
        key.replace('_', ' '): samba_value(value)
        for key, value in options.iteritems()
    }


@task
def setup():
    """
    Install samba
    """

    install()
    configure()


def install():
    with sudo():
        debian.apt_get('install', 'samba')


@task
def configure():
    """
    Configure samba
    """

    context = {
        'workgroup': blueprint.get('workgroup', 'WORKGROUP'),
        'shares': {name: sambafy_options(share)
                   for name, share in blueprint.get('shares', {}).iteritems()}
    }

    uploaded = blueprint.upload('./smb.conf', '/etc/samba/smb.conf', context)
    if uploaded:
        restart()
