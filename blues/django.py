import os
from jinja2 import Environment, FileSystemLoader
from fabric.context_managers import cd

from refabric.contrib.templates import blueprint_templates, get_jinja_environment, upload
from fabric.decorators import task
from fabric.operations import prompt
from refabric.state import blueprint_settings
from refabric.context_managers import silent, sudo
from refabric.contrib import debian
from . import git
from . import user
from . import virtualenv


settings = blueprint_settings(__name__)
templates = blueprint_templates(__name__)


@task
def manage(cmd=''):
    django_settings = settings('settings_module')

    if django_settings:
        django_settings = '--settings={}'.format(django_settings)

    if not cmd:
        cmd = prompt('Enter django management command:')

    print 'manage.py {cmd} {settings}'.format(cmd=cmd,
                                              settings=django_settings)
    repo = settings('git')


@task
def install():
    with sudo():
        # Create global paths
        root_path = get_app_root()
        debian.mkdir(root_path)

    # Create project user
    install_project_user()

    # Install system-dependencies
    install_deb_packages()

    # Clone repository
    install_git()

    # Create virtualenv
    install_virtualenv()

@task
def upgrade():
    # Reset git repo
    update_git()

    # Update uwsgi-configuration
    upload_server_conf()


def upload_server_conf():
    server = settings('server')
    if server['type'] == 'uwsgi':
        upload_uwsgi_conf()


def upload_uwsgi_conf():
    server = settings('server')
    project_name = settings('project')
    uwsgi_conf_path = '/etc/uwsgi/apps-available/{}.ini'.format(project_name)
    with sudo():
        context = {
            'server': server
        }
        upload(templates['uwsgi.ini'], uwsgi_conf_path, context)


def install_project_user():
    username = settings('project')
    home_path = get_project_home()

    # Get UID for project user
    user.create(username, home_path)
    # Upload deploy keys for project user
    user.upload_auth_keys(username, templates['deploy_keys'])
    user.set_strict_host_checking(username, 'github.com')


def install_deb_packages():
    django_packages = settings('deb_packages')
    debian.apt_get('install', *django_packages)


def install_virtualenv():
    username = settings('project')
    virtualenv.install()
    with sudo(username):
        virtualenv.create(get_virtualenv_path())
    install_requirements()


def install_requirements():
    path = get_virtualenv_path()
    requirements_path = os.path.join(get_git_path(), 'requirements.txt')
    virtualenv.pip('install', path, '-r {}'.format(requirements_path))


def install_git():
    git.install()

    project_name = settings('project')
    branch = settings('git_branch')
    git_url = settings('git_url')

    with sudo(project_name):
        source_path = get_source_path()
        debian.mkdir(source_path, owner=project_name, group=project_name)
        with cd(source_path):
            git_path = git.clone(git_url, branch)
            git.reset(git_path, branch)


def update_git():
    project_name = settings('project')
    with sudo(project_name):
        git_path = get_git_path()
        branch = settings('git_branch')
        git.reset(git_path, branch)


def get_project_home():
    return os.path.join(get_app_root(), settings('project'))


def get_app_root():
    return settings('root_path') or '/srv/app'


def get_source_path():
    return os.path.join(get_project_home(), 'src')


def get_git_path():
    project_name = settings('project')
    source_path = get_source_path()
    return os.path.join(source_path, '{}.git'.format(project_name))


def get_virtualenv_path():
    return os.path.join(get_project_home(), 'env')
