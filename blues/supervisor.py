from functools import partial
import os

from fabric.context_managers import cd
from fabric.contrib import files
from fabric.decorators import task
from fabric.utils import warn

from refabric.api import run, info
from refabric.context_managers import sudo, silent, hide_prefix
from refabric.contrib import blueprints

from . import debian
from . import python

__all__ = ['start', 'stop', 'restart', 'reload', 'setup', 'configure',
           'enable', 'disable', 'ctl']


blueprint = blueprints.get(__name__)

supervisord_root = '/etc/supervisord'
programs_available_path = os.path.join(supervisord_root, 'programs-available')
programs_enabled_path = os.path.join(supervisord_root, 'programs-enabled')
log_path = '/var/log/supervisord'
tmpfs_path = '/run/supervisord'


@task
def setup():
    """
    Install Supervisor and enable/disable configured programs
    """
    install()
    configure()


def install():
    with sudo():
        # Ensure python (pip) is installed
        python.install()

        # PIP install system wide Supervisor
        package = 'supervisor'
        version = blueprint.get('version')
        if version:
            package += '=={}'.format(version)
        info('Installing: {} ({})', 'Supervisor', version if version else 'latest')
        python.pip('install', package)

        # Create group
        debian.groupadd('app-data', gid_min=10000)

        # Create directories
        for d in (programs_available_path, programs_enabled_path, log_path, tmpfs_path):
            debian.mkdir(d, owner='root', group='app-data', mode=1775)


@task
def configure():
    """
    Enable/disable configured programs
    """
    with sudo():
        # Upload templates
        uploads = blueprint.upload('init/', '/etc/init/')
        uploads.extend(blueprint.upload('supervisord.conf', '/etc/'))

        # Disable previously enabled programs not configured programs-enabled
        changes = []
        programs = blueprint.get('programs') or []
        auto_disable = blueprint.get('auto_disable_programs', True)
        if auto_disable:
            with silent():
                enabled_program_links = run('ls {}'.format(programs_enabled_path)).split()
            for link in enabled_program_links:
                link_name = os.path.splitext(link)[0]  # Without extension
                if link not in programs and link_name not in programs:
                    changed = disable(link, do_reload=False)
                    changes.append(changed)

        ### Enable programs from settings
        for program in programs:
            changed = enable(program, do_reload=False)
            changes.append(changed)

        ### Reload supervisor if new templates or any program has been enabled/disabled
        if uploads or any(changes):
            reload()


@task
def disable(program, do_reload=True):
    """
    Disable program.

    :param program: Program to disable
    :param do_reload: Reload supervisor
    :return: Got disabled?
    """
    disabled = False
    program = program if program.endswith('.conf') or program == 'default' else '{}.conf'.format(program)
    with sudo(), cd(programs_enabled_path):
        if files.is_link(program):
            info('Disabling program: {}', program)
            with silent():
                debian.rm(program)
                disabled = True
            if do_reload:
                reload()
        else:
            warn('Invalid program: {}'.format(program))

    return disabled


@task
def enable(program, do_reload=True):
    """
    Enable program.

    :param program: Program to enable
    :param do_reload: Reload supervisor
    :return: Got enabled?
    """
    enabled = False
    program = program if program.endswith('.conf') or program == 'default' else '{}.conf'.format(program)

    with sudo():
        available_program = os.path.join(programs_available_path, program)
        if not files.exists(available_program):
            warn('Invalid program: {}'.format(program))
        else:
            with cd(programs_enabled_path):
                if not files.exists(program):
                    info('Enabling program: {}', program)
                    with silent():
                        debian.ln(available_program, program)
                        enabled = True
                    if do_reload:
                        reload()

    return enabled


@task
def ctl(command, program=''):
    """
    Run supervisorctl :[command],[program]

    :param command: The command to run
    :param program: The program to run command against
    """
    with sudo(), silent():
        output = run('supervisorctl {} {}'.format(command, program))
        with hide_prefix():
            info(output)


def service(command, program=None):
    if not program:
        debian.service('supervisor', command)
    else:
        if command == 'reload':
            command = 'restart'
        ctl(command, program)


start = task(partial(service, 'start'))
stop = task(partial(service, 'stop'))
restart = task(partial(service, 'restart'))
reload = task(partial(service, 'reload'))

start.__doc__ = 'Start supervisor or start program'
stop.__doc__ = 'Stop supervisor or stop program'
restart.__doc__ = 'Restart supervisor or restart program'
reload.__doc__ = 'Reload supervisor or restart program'


