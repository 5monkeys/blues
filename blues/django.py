import os
from contextlib import contextmanager
from fabric.context_managers import cd
from fabric.state import env
from fabric.utils import indent
from refabric.contrib import blueprints
from fabric.decorators import task
from fabric.operations import prompt, run
from refabric.context_managers import sudo, shell_env
from refabric.contrib import debian
from refabric.utils import info
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
    if not cmd:
        cmd = prompt('Enter django management command:')
    with sudo_project() as project, cd(git_path()), virtualenv.activate(virtualenv_path()), shell_env():
        run('python {project_name}/manage.py {cmd}'.format(project_name=project, cmd=cmd))


@task
def setup():
    install()
    upgrade()
    manage('syncdb')


def install():
    with sudo():
        # Create global paths
        root_path = app_root()
        debian.mkdir(root_path)

        # Create project user
        install_project_user()

        # Create static paths
        project_name = blueprint.get('project')
        static_base = os.path.join('/srv/www/', project_name)
        static_path = os.path.join(static_base, 'static')
        media_path = os.path.join(static_base, 'media')
        debian.mkdir(static_path, group='www-data')
        debian.chmod(static_path, mode=1775)
        debian.mkdir(media_path, group='www-data')
        debian.chmod(media_path, mode=1775)

        # Install system-dependencies
        install_system_dependencies()

        # Clone repository
        install_git()

        # Create virtualenv
        install_virtualenv()


@task
def upgrade():
    # Reset git repo
    update_git()

    # Install repo requirements.txt
    install_requirements()

    # Update uwsgi-configuration
    upload_server_conf()


def upload_server_conf():
    with sudo_project():
        server = blueprint.get('server')
        if server['type'] == 'uwsgi':
            upload_uwsgi_conf()

@task
def upload_uwsgi_conf():
    from blues import uwsgi
    project_name = blueprint.get('project')
    owner = debian.get_user(project_name)

    context = dict(owner)  # name, uid, gid, ...

    # Memory optimized options
    cpu_count = blueprint.get('server.max_cores', debian.nproc())
    total_memory = blueprint.get('server.max_memory',
                                 default=debian.total_memory() / 1024 / 1024 / 1024)
    workers = blueprint.get('server.workers', default=uwsgi.get_worker_count(cpu_count))

    info('Generating uWSGI conf based on {} core(s), {} GB memory and {} worker(s)',
         cpu_count, total_memory, workers)

    # TODO: Handle different loop engines (gevent)
    context.update({
        'cpu_affinity': uwsgi.get_cpu_affinity(cpu_count, workers),
        'workers': workers,
        'max_requests': uwsgi.get_max_requests(total_memory),
        'reload_on_as': uwsgi.get_reload_on_as(total_memory),
        'reload_on_rss': uwsgi.get_reload_on_rss(total_memory),
        'limit_as': uwsgi.get_limit_as(total_memory),
        'source': os.path.join(git_path(), project_name),
        'virtualenv': virtualenv_path(),
    })

    # Override defaults
    context.update(blueprint.get('server'))

    ini = '{}.ini'.format(project_name)
    template = os.path.join('uwsgi', ini)
    remote_conf = os.path.join(project_home(), 'uwsgi.d')
    updates = []
    # Check if a specific web vassal have been created or use the default
    if template not in blueprint.get_template_loader().list_templates():
        # Upload default web vassal
        info(indent('...using default web vassal'))
        template = os.path.join('uwsgi', 'default', 'web.ini')
        updates = blueprint.upload(template, os.path.join(remote_conf, ini), context=context)

    # Upload remaining vassals
    updated = blueprint.upload('uwsgi/', remote_conf, context=context)
    updates.extend(updated)
    if updates:
        uwsgi.reload()


@task
def generate_nginx_conf(role='www'):
    name = blueprint.get('project')
    socket = blueprint.get('server.socket', default='0.0.0.0:3030')
    host, _, port = socket.partition(':')
    if port:
        sockets = ['{}:{}'.format(host, port) for host in env.hosts]
    else:
        sockets = ['unix:{}'.format(socket)]

    context = {
        'name': name,
        'sockets': sockets,
        'domain': blueprint.get('server.domain', default='_'),
        'ssl': blueprint.get('server.ssl', False),
        'ip_hash': blueprint.get('server.ip_hash', False)
    }
    template = 'nginx/site.conf'
    server_type = blueprint.get('server.type')
    if server_type and server_type == 'uwsgi':
        template = 'nginx/uwsgi_site.conf'
    conf = blueprint.render_template(template, context)
    conf_dir = os.path.join(os.path.dirname(env['real_fabfile']), 'templates', role, 'nginx',
                            'sites-available')
    conf_path = os.path.join(conf_dir, '{}.conf'.format(name))

    if not os.path.exists(conf_dir):
        os.makedirs(conf_dir)

    with open(conf_path, 'w+') as f:
        f.write(conf)


def install_project_user():
    username = blueprint.get('project')
    home_path = project_home()

    # Get UID for project user
    user.create(username, home_path, groups=['app-data', 'www-data'])
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
    with sudo_project():
        path = virtualenv_path()
        pip_log_path = os.path.join(project_home(), '.pip', 'pip.log')
        requirements_path = os.path.join(git_path(), 'requirements.txt')
        with virtualenv.activate(path):
            virtualenv.pip('install', '-r {} --log={}'.format(requirements_path, pip_log_path))


def install_git():
    git.install()

    branch = blueprint.get('git_branch')
    git_url = blueprint.get('git_url')

    with sudo_project() as project:
        path = source_path()
        debian.mkdir(path, owner=project, group=project)
        with cd(path):
            git.clone(git_url, branch)


def update_git():
    with sudo_project():
        path = git_path()
        branch = blueprint.get('git_branch')
        with cd(path):
            git.reset(branch)


@contextmanager
def sudo_project():
    project_name = blueprint.get('project')
    with sudo(project_name):
        yield project_name
