import os
from pprint import pprint
from fabric.context_managers import cd
from fabric.state import env
from refabric.contrib import blueprints
from fabric.decorators import task
from fabric.operations import prompt
from refabric.context_managers import sudo
from refabric.contrib import debian
from . import git
from . import user
from . import virtualenv

blueprint = blueprints.get(__name__)

project_home = lambda: os.path.join(app_root(), blueprint.get('project'))
app_root = lambda: blueprint.get('root_path') or '/srv/app'
source_path = lambda: os.path.join(project_home(), 'src')
git_path = lambda: os.path.join(source_path(), '{}.git'.format(blueprint.get('project')))
virtualenv_path = lambda: os.path.join(project_home(), 'env')


@task
def manage(cmd=''):
    django_settings = blueprint.get('settings_module')

    if django_settings:
        django_settings = '--settings={}'.format(django_settings)

    if not cmd:
        cmd = prompt('Enter django management command:')

    print 'manage.py {cmd} {settings}'.format(cmd=cmd,
                                              settings=django_settings)
    repo = blueprint.get('git')


@task
def install():
    with sudo():
        # # Create global paths
        root_path = app_root()
        debian.mkdir(root_path)

        # Create project user
        install_project_user()

        # Install system-dependencies
        install_system_dependencies()

        # Clone repository
        install_git()

        # Create virtualenv
        install_virtualenv()


@task
def upgrade():
    project_name = blueprint.get('project')
    with sudo(project_name):
        # Reset git repo
        update_git()

        # Install repo requirements.txt
        install_requirements()

        # Update uwsgi-configuration
        upload_server_conf()


def upload_server_conf():
    server = blueprint.get('server')
    if server['type'] == 'uwsgi':
        upload_uwsgi_conf()


def upload_uwsgi_conf():
    project_name = blueprint.get('project')
    owner = debian.get_user(project_name)

    context = dict(owner)  # name, uid, gid, ...
    context.update(blueprint.get('server'))  # workers, ...
    context.update({
        'source': git_path(),
        'virtualenv': virtualenv_path(),

    })

    remote_conf = os.path.join(project_home(), 'uwsgi.d')
    blueprint.upload('uwsgi/', remote_conf, context=context)

@task
def generate_uwsgi_upstream(role='www'):
    name = blueprint.get('project')
    socket = blueprint.get('server.socket', default='0.0.0.0:3030')
    host, _, port = socket.partition(':')
    if port:
        sockets = ['{}:{}'.format(host, port) for host in env.hosts]
    else:
        sockets = [socket]

    context = {
        'name': name,
        'sockets': sockets,
        'ip_hash': blueprint.get('server.ip_hash', False)
    }

    upstream = blueprint.render_template('nginx/upstream.conf', context)
    upstream_dir = os.path.join(os.path.dirname(env['real_fabfile']),
                                'templates', role, 'nginx', 'conf.d')
    upstream_path = os.path.join(upstream_dir, '{}.conf'.format(name))

    if not os.path.exists(upstream_dir):
        os.makedirs(upstream_dir)

    with open(upstream_path, 'w+') as f:
        f.write(upstream)


def install_project_user():
    username = blueprint.get('project')
    home_path = project_home()

    # Get UID for project user
    user.create(username, home_path, groups=['app-data'])
    # Upload deploy keys for project user
    user.set_strict_host_checking(username, 'github.com')


def install_system_dependencies():
    django_dependencies = blueprint.get('system_dependencies')
    if django_dependencies:
        debian.apt_get('install', *django_dependencies)


def install_virtualenv():
    username = blueprint.get('project')
    virtualenv.install()
    with sudo(username):
        virtualenv.create(virtualenv_path())


def install_requirements():
    path = virtualenv_path()
    pip_log_path = os.path.join(project_home(), '.pip', 'pip.log')
    requirements_path = os.path.join(git_path(), 'requirements.txt')
    with virtualenv.activate(path):
        virtualenv.pip('install', '-r {} --log={}'.format(requirements_path, pip_log_path))


def install_git():
    git.install()

    project_name = blueprint.get('project')
    branch = blueprint.get('git_branch')
    git_url = blueprint.get('git_url')

    with sudo(project_name):
        path = source_path()
        debian.mkdir(path, owner=project_name, group=project_name)
        with cd(path):
            git.clone(git_url, branch)


def update_git():
    path = git_path()
    branch = blueprint.get('git_branch')
    with cd(path):
        git.reset(branch)
