"""
Debian Utils
============

Useful debian commands for other blueprints to use.
"""
import base64
import os
from contextlib import contextmanager
from functools import partial

import fabric.api
import fabric.operations
import fabric.contrib.files
import fabric.contrib.project
import fabric.context_managers
from fabric.colors import magenta
from fabric.decorators import task
from fabric.utils import abort, puts, indent, warn

from refabric.context_managers import silent, sudo
from refabric.operations import run
from refabric.utils import info


def chmod(location, mode=None, owner=None, group=None, recursive=False):
    if mode:
        run('chmod %s %s %s' % (recursive and '-R ' or '', mode,  location))
    if owner:
        chown(location, owner=owner, group=group, recursive=recursive)
    elif group:
        chgrp(location, group, recursive=recursive)


def chown(location, owner, group=None, recursive=False):
    owner = '{}:{}'.format(owner, group if group else owner)
    run('chown {} {} {}'.format(recursive and '-R ' or '', owner, location))


def chgrp(location, group, recursive=False):
    run('chgrp %s %s %s' % (recursive and '-R ' or '', group, location))


def rm(location, recursive=False, force=True):
    force = '-f' if force else ''
    recursive = '-r' if recursive else ''
    run('rm %s %s %s' % (force, recursive, location))


def cp(source, destination, force=True, mode=None, owner=None, group=None):
    force = force and '-f' or ''
    run('cp %s %s %s' % (force, source, destination))
    chmod(destination, mode, owner, group)


def mv(source, destination, force=True):
    force = force and '-f' or ''
    run('mv %s %s %s' % (force, source, destination))


def ln(source, destination, symbolic=True, force=True, mode=None,
       owner=None, group=None):
    force = force and '-f' or ''
    symbolic = symbolic and '-sn' or ''
    run('ln %s %s "%s" "%s"' % (symbolic, force, source, destination))
    chmod(destination, mode, owner, group)


def mkdir(location, recursive=True, mode=None, owner=None, group=None):
    with silent(), sudo():
        result = run('test -d "%s" || mkdir %s %s "%s"'
                     % (location,
                        mode and '-m %s' % mode or '',
                        recursive and '-p' or '',
                        location))

        if result.succeeded:
            if owner or group:
                chmod(location, owner=owner, group=group)
        else:
            raise Exception('Failed to create directory %s, %s'
                            % (location, result.stdout))


def mktemp(directory=False, mode=None):
    with silent(), sudo():
        cmd = 'mktemp'
        if directory:
            cmd += ' -d'
        output = run(cmd)
        path = output.stdout
        if directory:
            path += os.path.sep
        if mode:
            chmod(path, mode=mode)
        return path


@contextmanager
def temporary_dir(mode=None):
    path = mktemp(directory=True, mode=mode)
    try:
        yield path
    finally:
        rm(path, recursive=True)


def lsb_release():
    return run('lsb_release --release --short')
lbs_release = lsb_release  # Backwards compatibility


def lsb_codename():
    return run('lsb_release --codename --short')
lbs_codename = lsb_codename  # Backwards compatibility


def hostname():
    return run('hostname -A').stdout.strip()


def apt_get(command, *options):
    options = ' '.join(options) if options else ''

    return run('apt-get --yes {} {}'.format(command, options))


def apt_get_update(quiet=True):
    options = '-q' if quiet else ''
    info('Updating apt package lists')
    return run('apt-get {} update'.format(options))


def debconf_set_selections(*selections):
    for selection in selections:
        run('echo debconf "{}" | debconf-set-selections'.format(selection))


def debconf_communicate(command, package):
    run('echo {} | debconf-communicate {}'.format(command.upper(), package))


def dpkg_query(package):
    status = run("dpkg-query -W -f='${Status}' %s ; true" % package)
    return 'not-installed' not in status and 'installed' in status


def add_apt_repository(repository, accept=True, src=False):
    if src:
        run('add-apt-repository "{}" {}'.format(repository,
                                                '--yes' if accept else ''))
    else:
        # Add repository manually to sources.list due to ubuntu bug
        if not repository.startswith('deb '):
            repository = 'deb {}'.format(repository)
        fabric.contrib.files.append('/etc/apt/sources.list', repository,
                                    shell=True)


def add_apt_key(url):
    run('wget -O - {url} | apt-key add -'.format(url=url))


def add_apt_ppa(name, accept=True, src=False):
    with sudo(), fabric.context_managers.cd('/etc/apt/sources.list.d'):
        source_list = '%s-%s.list' % (name.replace('/', '-'), lbs_codename())

        if not fabric.contrib.files.exists(source_list):
            add_apt_repository('ppa:{}'.format(name), accept=accept, src=src)
            apt_get_update()


def command_exists(*command):
    with fabric.context_managers.quiet():
        return all((
            run("which '%s' >& /dev/null" % c).succeeded
            for c in command
        ))


def get_user(name):
    with silent():
        d = run("cat /etc/passwd | egrep '^%s:' ; true" % name, user='root')
        s = run("cat /etc/shadow | egrep '^%s:' | awk -F':' '{print $2}'"
                % name,
                user='root')

    results = {}
    if d:
        d = d.split(':')
        assert len(d) >= 7, "/etc/passwd entry is expected to have at least 7 fields, " \
                            "got %s in: %s" % (len(d), ':'.join(d))
        results = dict(name=d[0], uid=d[2], gid=d[3], home=d[5], shell=d[6])
    if s:
        results['passwd'] = s
    if results:
        return results
    else:
        return None


def get_group(name):
    group_data = run("cat /etc/group | egrep '^%s:' ; true" % name)
    if group_data:
        name, _, gid, members = group_data.split(':', 4)
        return dict(name=name, gid=gid, members=tuple(m.strip() for m in members.split(',') if m.strip()))
    else:
        return None


def groupadd(name, gid=None, gid_min=None, gid_max=None, system=False):
    group = get_group(name)
    if not group:
        options = []
        if gid:
            options.append("-g '%s'" % gid)
        if gid_min:
            options.append("-K GID_MIN='%s'" % gid_min)
        if gid_max:
            options.append("-K GID_MAX='%s'" % gid_max)
        if system:
            options.append('-r')
        run("groupadd %s '%s'" % (' '.join(options), name))
    else:
        if gid is not None and group.get('gid') != gid:
            groupmod(name, gid)


def groupmod(name, gid):
    run("groupmod -g %s '%s'" % (gid, name))


def useradd(name, home=None, create_home=False, shell=None, uid=None, uid_min=None, uid_max=None,
            user_group=False, gid=None, groups=None, system=False, password=None):
    """
    Create a new user or update default new user information

    :param name: The username
    :param home: Home directory of the new account. Will not create dir. *(Optional)*
    :param create_home: Create the user's home directory *(Default: False)*
    :param shell: Login shell of the new account *(Optional)*
    :param user_group: Create a group with the same name as the user *(Default: False)*
    :param uid: User ID of the new account *(Optional)*
    :param uid_min: Min value for automatic user/group ID selection *(Optional)*
    :param uid_max: Max value for automatic user/group ID selection *(Optional)*
    :param gid: Name or ID of the primary group of the new account *(Optional)*
    :param groups: List of supplementary groups of the new account *(Optional)*
    :param system: Create a system account *(Optional)*
    :param password: Encrypted password of the new account *(Optional)*
    """
    user = get_user(name)

    if not user:
        options = []
        if home:
            options.append("-d '%s'" % home)  # home directory of the new account (will not create)

        if create_home:
            options.append('-m')  # create the user's home directory
        else:
            options.append("-M")  # do not create the user's home directory

        if system:
            options.append('-r')  # create a system account

        if uid:
            options.append("-u '%s'" % uid)  # user ID of the new account

        if groups:
            options.append("-G '%s'" % ','.join(groups))  # list of supplementary groups of the new account

        if user_group:
            options.append("-U")  # create a group with the same name as the user
            if not gid and get_group(name):
                gid = name  # Automatically set gid to user name if the group already exists, otherwise useradd fails.
        else:
            options.append("-N")  # do not create a group with the same name as the user

        if gid:
            options.append("-g '%s'" % gid)  # name or ID of the primary group of the new account

        if shell:
            options.append("-s '%s'" % shell)  # login shell of the new account

        if uid_min:
            options.append("-K UID_MIN='%s'" % uid_min)  # Min value for automatic user ID selection
            if user_group:
                options.append("-K GID_MIN='%s'" % uid_min)  # Min value for automatic group ID selection

        if uid_max:
            options.append("-K UID_MAX='%s'" % uid_max)  # Max value for automatic user ID selection
            if user_group:
                options.append("-K GID_MAX='%s'" % uid_max)  # Max value for automatic group ID selection

        if password:
            options.append("-p %s" % password)  # encrypted password of the new account

        # Create the user
        run("useradd {options} '{username}'".format(options=' '.join(options), username=name))

    else:
        usermod(user, password=password, home=home, uid=uid, gid=gid, groups=groups, shell=shell)


def usermod(user, password=None, home=None, uid=None, gid=None, groups=None, shell=None):
    if isinstance(user, basestring):
        user = get_user(user)

    options = []
    if home is not None and user.get('home') != home:
        options.append("-d '%s'" % home)
    if uid is not None and user.get('uid') != uid:
        options.append("-u '%s'" % uid)
    if gid is not None and user.get('gid') != gid:
        options.append("-g '%s'" % gid)
    if groups:
        options.append("-a -G '%s'" % ','.join(groups))
    if shell is not None and user.get('shell') != shell:
        options.append("-s '%s'" % shell)
    if options:
        run("usermod %s '%s'" % (' '.join(options), user['name']))
    if password:
        chpasswd(user['name'], password)


def chpasswd(name, password, encrypted_passwd=False):
    with silent():
        encoded_password = base64.b64encode('%s:%s' % (name, password))
        encryption = ' -e' if encrypted_passwd else ''
        run('echo %s | base64 --decode | chpasswd%s' % encoded_password, encryption)


def pwd():
    with silent():
        return run('pwd').stdout.strip()


def service(name, action, check_status=True, show_output=False):
    c = fabric.context_managers
    with sudo('root'), c.settings(c.hide('running', 'stdout', 'stderr', 'warnings'), warn_only=True):
        info('Service: {} {}', name, action)

        if check_status:
            output = run('service {} status'.format(name), pty=False, combine_stderr=True)
            if output.return_code != 0:
                puts(indent(magenta(output)))
                return
            elif action in output:
                puts(indent('...has status {}'.format(magenta(output[len(name)+1:]))))
                return

        output = run('service {} {}'.format(name, action), pty=False, combine_stderr=True)
        if output.return_code != 0 or show_output:
            puts(indent(magenta(output)))


def service_task(name, action, check_status=False, show_output=False):
    partial_service = partial(service, name, action, check_status, show_output)
    pretty_action = action.replace('-', ' ').capitalize()
    partial_service.__doc__ = '{} {}'.format(pretty_action, name)
    return task(partial_service)


def update_rc(basename, priorities, force=False):
    run('update-rc.d {} {} {}'.format('-f' if force else '',
                                      basename,
                                      priorities), pty=False, use_sudo=True)


def add_rc_service(name, priorities='defaults'):
    update_rc(name, priorities)


def remove_rc_service(name):
    update_rc(name, priorities='remove', force=True)


def nproc():
    """
    Get the number of CPU cores.
    """
    c = fabric.context_managers
    with c.settings(c.hide('running', 'stdout')):
        res = run('nproc').strip()
        return int(res)


def total_memory():
    """
    Get total memory in bytes
    """
    c = fabric.context_managers
    with c.settings(c.hide('running', 'stdout')):
        memory = int(run("grep MemTotal /proc/meminfo | awk '{print $2}'"))
        # Convert to bytes
        memory *= 1024
        return memory


def page_size():
    """
    Get PAGE_SIZE
    """
    c = fabric.context_managers
    with c.settings(c.hide('running', 'stdout')):
        return int(run('getconf PAGE_SIZE').strip())


def phys_pages():
    """
    Get _PHYS_PAGES
    """
    c = fabric.context_managers
    with c.settings(c.hide('running', 'stdout')):
        return int(run('getconf _PHYS_PAGES').strip())


def set_timezone(timezone):
    """
    Set OS timezone

    :param timezone: Europe/Stockholm
    """
    with silent():
        run('ln -sf /usr/share/zoneinfo/{} /etc/localtime'.format(timezone))


def kill(sig, process, use_pkill=False):
    with sudo():
        with silent('warnings'):
            if use_pkill:
                output = run('pkill -{} {}'.format(sig, process))
            else:
                output = run('kill -{} {}'.format(sig, process))

        if output.return_code != 0:
            warn('No process got {} signal'.format(sig))
        else:
            info('Successfully sent {} signal to {}', sig, process)


@task
def sighup(process=None):
    """
    Send SIGHUP signal to process

    :param process: PID of process
    """
    if not process:
        abort('Missing process argument, sighup:<process>')

    kill('HUP', process)


def get_mount(mount_point):
    """
    Resolve a mount point to mounted file system.
    If not mounted, return None.

    :param str mount_point: Name of mount point to reslve
    :return str: Mounted file system
    """
    with silent('warnings'):
        output = run('egrep ".+ {} .+" /proc/mounts'.format(mount_point))
        if output.return_code == 0:
            file_system = output.stdout.split()[0]
            return file_system


def is_mounted(mount_point):
    """
    Check if mount point is mounted.

    :param mount_point: Name of mount point
    :return bool:
    """
    return get_mount(mount_point) is not None


def mount(mount_point, owner=None, group=None, **fstab):
    """
    Mount and optionally add configuration to fstab.

    :param str mount_point: Name of mount point
    :param str owner: Name of mount point owner
    :param str group: Name of mount point group
    :param dict fstab: Optional kwargs passed to add_fstab()
    """
    with sudo():
        if fstab:
            add_fstab(mount_point=mount_point, **fstab)

        # Mount
        if not is_mounted(mount_point):
            # Ensure mount point dir exists
            mkdir(mount_point, owner=owner, group=group, mode=755)

            with silent():
                info('Mounting {}', mount_point)
                run('mount {}'.format(mount_point))


def unmount(mount_point):
    """
    Unmount mount point.

    :param str mount_point: Name of mount point to unmount
    """
    with sudo(), silent():
        info('Unmounting {}', mount_point)
        run('umount {}'.format(mount_point))


def add_fstab(filesystem=None, mount_point=None, type='auto', options='rw', dump='0', pazz='0'):
    """
    Add mount point configuration to /etc/fstab.
    If mount point already mounted on different file system then unmount.

    :param str filesystem: The partition or storage device to be mounted
    :param str mount_point: The mount point where <filesystem> is mounted to
    :param str type: The file system type (Default: auto)
    :param str options: Mount options of the filesystem (Default: rw)
    :param str dump: Used by the dump utility to decide when to make a backup, 0|1 (Default: 0)
    :param str pazz: Used by fsck to decide which order filesystems are to be checked (Default: 0)
    """
    with sudo():
        fstab_line = '{fs} {mount} {type} {options} {dump} {pazz}'.format(
            fs=filesystem,
            mount=mount_point,
            type=type,
            options=options,
            dump=dump,
            pazz=pazz
        )

        # Add mount to /etc/fstab if not already there (?)
        with silent():
            output = run('cat /etc/fstab')
            fstab = output.stdout
            if fstab_line not in fstab.split('\n'):  # TODO: Handle comments
                info('Adding fstab: {} on {}', filesystem, mount_point)
                fabric.contrib.files.append('/etc/fstab', fstab_line, use_sudo=True)

        # Unmount any previous mismatching mount point
        mounted_file_system = get_mount(mount_point)
        if mounted_file_system and mounted_file_system != filesystem:
            unmount(mount_point)


def locale_gen(locale, utf8=True):
    locale_gen_cmd = 'locale-gen {}'.format(locale)
    locale_gen_utf8_cmd = locale_gen_cmd + '.UTF-8'

    with sudo():
        run(locale_gen_cmd)
        if utf8:
            run(locale_gen_utf8_cmd)
