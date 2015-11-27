"""
Python Blueprint
================

Does not install python itself, only develop and setup tools.
Contains pip helper for other blueprints to use.

**Fabric environment:**

.. code-block:: yaml

    blueprints:
      - blues.python

"""
from fabric.decorators import task

from refabric.api import run, info
from refabric.context_managers import sudo
from refabric.contrib import blueprints

from . import debian

__all__ = ['setup', 'requested_version']


pip_log_file = '/tmp/pip.log'
blueprint = blueprints.get(__name__)


def requested_version():
    ver = blueprint.get('version', '2.7')  # Default to python 2.7
    return tuple(map(int, str(ver).split('.')))[:2]


@task
def setup():
    """
    Install python develop tools
    """
    install()


@task
def version():
    if not hasattr(version, 'version'):
        version_string = run('python --version').stdout
        _, ver = version_string.split(' ')
        version.version = tuple(map(int, ver.split('.')))

    return version.version


def install():
    with sudo():
        info('Install python dependencies')

        req_ver = requested_version()

        # Install python 2.7 easy_install
        debian.apt_get('install', 'python-setuptools')

        if req_ver < (3, 0):
            # This assumes < 3.0 means "debian default python".
            # Python 2.7 is the default on Debian at the moment, so we just
            # need to install the headers for later use by compiled modules.
            debian.apt_get('install', 'python-dev')
        else:
            # We need to install a non-default python version.

            v_milestone = '.'.join(map(str, req_ver[:2]))  # e.g. "3.4"
            v_major = str(req_ver[0])  # e.g. "3"

            # Util: easily make python package name.
            def py_pkg(ver, suffix=''):
                return 'python' + ver + suffix

            debian.apt_get('install',
                           py_pkg(v_milestone),
                           py_pkg(v_milestone, '-dev'),
                           py_pkg(v_major, '-pip'))

        # Install python default pip.
        run('easy_install pip')

        # Create pip log file
        run('touch {}'.format(pip_log_file))
        debian.chmod(pip_log_file, mode=777)

        # Install latest setuptools via pip, since debian has on old version.
        pip('install', 'setuptools', '--upgrade')


def pip(command, *options, **kwargs):
    # TODO: change pip log location, per env? per user?
    # Perhaps we should just remove the log_file argument and let pip put it
    # where it belongs.
    info('Running pip {}', command)
    bin = kwargs.pop('bin',
                     'pip3' if requested_version() >= (3,)
                     else 'pip')
    cmd = '{pip} {command} {options} -v --log={log_file} --log-file={log_file}'

    run(cmd.format(pip=bin, command=command,
                   options=' '.join(options), log_file=pip_log_file))


@task
def update_pip():
    info('Updating pip')
    pip('install -U pip')
