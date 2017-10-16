"""
Samba Blueprint
===================

**Fabric environment:**

.. code-block:: yaml

    blueprints:
      - blues.samba

    settings:
      samba:
        workgroup: WORKGROUP            # default: WORKGROUP

        shares:
          - name: SOME_NAME             # required
            comment: "Some comment"     # optional
            path: "/path/to/be/shared"  # required
            public: true                # default: false
            browseable: true            # default: true
            writeable: true             # default: true
            read_only: false            # default: false
            create_mask: 0777           # default: 0777
            directory_mask: 0777        # default: 0777
            force_user: some_user       # optional
            guest_ok: false             # default: false

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

_SHARE_DEFAULTS = {
    'public': False,
    'browseable': True,
    'writeable': True,
    'read_only': False,
    'create_mask': '0777',
    'directory_mask': '0777',
    'guest_ok': False,
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
        'shares': [dict(_SHARE_DEFAULTS, **share)
                   for share in blueprint.get('shares', [])]
    }

    uploaded = blueprint.upload('./smb.conf', '/etc/samba/smb.conf', context)
    if uploaded:
        restart()
