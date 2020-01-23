import os
from functools import partial

from fabric.context_managers import cd
from fabric.state import env
from fabric.utils import indent, abort, warn
from blues.application.project import git_repository_path

from refabric.context_managers import sudo, silent
from refabric.operations import run
from refabric.utils import info
from refabric.contrib import blueprints

from .providers import get_providers

from .. import debian
from .. import git
from .. import user
from .. import python
from .. import util
from .. import virtualenv

__all__ = [
    'install_project',
    'install_project_user',
    'install_project_structure',
    'install_system_dependencies',
    'install_virtualenv',
    'install_requirements',
    'install_or_update_source',
    'install_source',
    'update_source',
    'install_providers'
]


blueprint = blueprints.get('blues.app')


def install_project():
    create_app_root()
    install_project_user()
    install_project_structure()
    install_system_dependencies()
    install_or_update_source()


def create_app_root():
    from .project import app_root

    with sudo():
        # Create global apps root
        root_path = app_root()
        debian.mkdir(root_path, recursive=True)


def install_project_user():
    """
    Create project user and groups.
    Create user home dir.
    Disable ssh host checking.
    Create log dir.
    """
    from .project import project_home, user_name, log_path

    with sudo():
        info('Install application user')
        username = user_name()
        home_path = project_home()

        # Setup groups for project user
        project_user_groups = ['app-data', 'www-data']
        for group in project_user_groups:
            debian.groupadd(group, gid_min=10000)

        # Get UID for project user
        user.create_system_user(username, groups=project_user_groups,
                                home=home_path)

        # Ensure project home has right owner in case user already exists
        debian.mkdir(home_path, owner=username, group=username, mode=1775)

        # Create application log path
        debian.mkdir(log_path(), owner=username, group='app-data', mode=1775)

        # Configure ssh for github
        user.set_strict_host_checking(username, 'github.com')

    dirs = blueprint.get('directories') or []
    if dirs:
        info('Create application directories')
    for d in dirs:
        if isinstance(d, basestring):
            d = {'path': d}
        info('  %s' % d['path'])
        mode = d.get('mode')
        debian.mkdir(d['path'], recursive=True,
                     owner=d.get('owner') or username,
                     group=d.get('group') or 'app-data',
                     mode=int(mode) if mode else 1775)


def install_project_structure():
    """
    Create project directory structure
    """
    from .project import static_base, use_static

    with sudo():
        info('Install application directory structure')

        create_app_root()

        if use_static():
            # Create static web paths
            static_path = os.path.join(static_base(), 'static')
            media_path = os.path.join(static_base(), 'media')
            debian.mkdir(static_path, group='www-data', mode=1775)
            debian.mkdir(media_path, group='www-data', mode=1775)


def install_system_dependencies():
    """
    Install system wide packages that application depends on.
    """
    with sudo(), silent():
        info('Install system dependencies')
        system_dependencies = blueprint.get('system_dependencies')

        if system_dependencies:
            dependencies = []
            repositories = []
            ppa_dependencies = []
            for dependency in system_dependencies:
                dep, _, rep = dependency.partition('@')
                if rep:
                    if rep not in repositories:
                        repositories.append(rep)

                    ppa_dependencies.append(dep)
                elif dep not in dependencies:
                    dependencies.append(dep)

            debian.apt_get_update()
            debian.apt_get('install', *dependencies)

            if repositories:
                for repository in repositories:
                    debian.add_apt_repository(repository, src=True)

                debian.apt_get_update()
                debian.apt_get('install', *ppa_dependencies)


def install_virtualenv():
    """
    Create a project virtualenv.
    """
    from .project import sudo_project, virtualenv_path

    with sudo():
        virtualenv.install()

    with sudo_project():
        virtualenv.create(virtualenv_path())

    with virtualenv.activate(virtualenv_path()):
        python.upgrade_setuptools()


def maybe_install_requirements(previous_commit, current_commit, force=False, update_pip=False):
    from .project import requirements_txt, git_repository_path

    changed_files = []

    commit_range = '{}..{}'.format(previous_commit, current_commit)

    installation_files = requirements_txt()

    if force:
        changed_files = installation_files

    else:
        with sudo(), cd(git_repository_path()), silent():
            tree = util.RequirementTree(paths=installation_files)

        for installation_file in tree.all_files():
            installation_method = get_installation_method(installation_file)

            if not force:
                if installation_method == 'pip':
                    has_changed, added, removed = diff_requirements(
                        previous_commit,
                        current_commit,
                        installation_file)

                    if has_changed:
                        info('Requirements have changed, '
                             'added: {}, removed: {}'
                             .format(', '.join(added), ', '.join(removed)))
                else:
                    # Check if installation_file has changed
                    has_changed, _, _ = git.diff_stat(
                        git_repository_path(),
                        commit_range,
                        installation_file)

                if has_changed:
                    changed_files.append(installation_file)

        changed_files = tree.get_changed(all_changed_files=changed_files)

    if changed_files:
        info('Install requirements {}', ', '.join(changed_files))
        install_requirements(changed_files, update_pip=update_pip)
    else:
        info(indent('(requirements not changed in {}...skipping)'),
             commit_range)


def diff_requirements(previous_commit, current_commit, filename):
    """
    Diff requirements file

    :param previous_commit:
    :param current_commit:
    :param filename:
    :return: 3-tuple with (has_changed, additions, removals) where
        has_changed is a bool, additions and removals may be sets or None.
    """
    try:
        return diff_requirements_smart(previous_commit,
                                       current_commit,
                                       filename,
                                       strict=True)
    except ValueError:
        warn('Smart requirements diff failed, falling back to git diff')

    has_changed, insertions, deletions = git.diff_stat(
        git_repository_path(),
        '{}..{}'.format(previous_commit, current_commit),
        filename)

    return has_changed, [str(insertions)], [str(deletions)]


def diff_requirements_smart(previous_commit, current_commit, filename,
                            strict=False):

    get_requirements = partial(git.show_file,
                               repository_path=git_repository_path(),
                               filename=filename)

    force_changed = False

    try:
        text = get_requirements(revision=previous_commit)
        previous = set(util.iter_requirements(text=text))
    except ValueError as exc:
        warn('Failed to parse previous requirements: {}'.format(exc))
        previous = set()
        force_changed = True

        if strict:
            raise

    try:
        text = get_requirements(revision=current_commit)
        current = set(util.iter_requirements(text=text))
    except ValueError as exc:
        warn('Failed to parse new requirements: {}'.format(exc))
        current = set()
        force_changed = True

        if strict:
            raise

    additions = current.difference(previous)
    removals = previous.difference(current)

    has_changed = force_changed or bool(additions or removals)

    return has_changed, additions, removals


def get_installation_method(filename):
    if filename.endswith('.txt') or \
            filename.endswith('.pip'):
        return 'pip'

    if os.path.basename(filename) == 'setup.py':
        return 'setuptools'


def install_requirements(installation_files=None, update_pip=False):
    """
    Pip install requirements in project virtualenv.
    """
    from .project import sudo_project, virtualenv_path, requirements_txt, \
        git_repository_path

    if not installation_files:
        installation_files = requirements_txt()

    if isinstance(installation_files, basestring):
        installation_files = [installation_files]

    with sudo_project():
        path = virtualenv_path()

        for installation_file in installation_files:
            info('Installing requirements from file {}', installation_file)

            with virtualenv.activate(path), cd(git_repository_path()):
                installation_method = get_installation_method(installation_file)
                if installation_method == 'pip':
                    if update_pip:
                        python.update_pip()
                    python.pip('install', '-r', installation_file)
                elif installation_method == 'setuptools':
                    with cd(git_repository_path()):
                        run('python {} develop'.format(installation_file))
                else:
                    raise ValueError(
                        '"{}" is not a valid installation file'.format(
                            installation_file))


def install_or_update_source():
    """
    Try to install source, if already installed then update.
    """
    new_install = install_source()
    if not new_install:
        update_source()


def install_source():
    """
    Install git and clone application repository.

    :return: True, if repository got cloned
    """
    from .project import sudo_project, git_repository, git_root

    with sudo():
        git.install()

    with sudo_project() as username:
        path = git_root()
        debian.mkdir(path, owner=username, group=username)
        with cd(path):
            repository = git_repository()
            path, cloned = git.clone(repository['url'], branch=repository['branch'])
            if cloned is None:
                abort('Failed to install source, aborting!')

    return cloned


def update_source():
    """
    Update application repository with configured branch.

    :return: tuple(previous commit, current commit)
    """
    from .project import sudo_project, git_repository_path, git_repository

    with sudo_project():
        # Get current commit
        path = git_repository_path()
        previous_commit = git.get_commit(path, short=True)

        # Update source from git (reset)
        repository = git_repository()
        current_commit = git.reset(repository['branch'],
                                   repository_path=path,
                                   ignore=blueprint.get('git_force_ignore'))

        if current_commit is not None and current_commit != previous_commit:
            info(indent('(new version)'))
        else:
            info(indent('(same commit)'))

        return previous_commit, current_commit


def install_providers():
    """
    Install application providers on current host.
    """
    host = env.host_string
    providers = get_providers(host)
    for provider in providers.values():
        if getattr(provider, 'manager', None) is not None:
            provider.manager.install()

        provider.install()
