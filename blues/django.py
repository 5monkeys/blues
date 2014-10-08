import os
from contextlib import contextmanager

from fabric.context_managers import cd, settings
from fabric.decorators import task
from fabric.operations import prompt
from fabric.state import env
from fabric.utils import indent

from refabric.api import run, info
from refabric.context_managers import sudo, shell_env
from refabric.contrib import blueprints, debian

from . import git
from . import user
from . import virtualenv

blueprint = blueprints.get(__name__)

project_home = lambda: os.path.join(app_root(), blueprint.get('project'))
app_root = lambda: blueprint.get('root_path') or '/srv/app'
source_path = lambda: os.path.join(project_home(), 'src')
virtualenv_path = lambda: os.path.join(project_home(), 'env')


@task
def manage(cmd=''):
    if not cmd:
        cmd = prompt('Enter django management command:')
    with sudo_project(), cd(git_path()), virtualenv.activate(virtualenv_path()), shell_env():
        run('python manage.py {cmd}'.format(cmd=cmd))


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
    upload_daemon_conf()


@task
def upload_daemon_conf():
    from blues import uwsgi
    updates = []

    with sudo_project():
        default_templates = uwsgi.blueprint.get_default_template_root()
        destination = os.path.join(project_home(), 'uwsgi.d')
        debian.mkdir(destination)

        with settings(template_dirs=[default_templates]):
            wsgi_daemon = blueprint.get('wsgi.daemon')
            if wsgi_daemon == 'uwsgi':
                context = get_uwsgi_wsgi_context()

                wsgi_vassals = upload_uwsgi_wsgi_conf(destination, context=context)
                if wsgi_vassals:
                    updates.extend(wsgi_vassals)

                # Upload remaining vassals
                user_vassals = blueprint.upload('uwsgi/', destination, context=context)  # TODO: skip subdirs
                if user_vassals:
                    updates.extend(user_vassals)

            celery_daemon = blueprint.get('celery.daemon')
            if celery_daemon == 'uwsgi':
                celery_vassals = upload_uwsgi_celery_conf(destination)
                if celery_vassals:
                    updates.extend(celery_vassals)

    if updates:
        uwsgi.restart()


def get_uwsgi_wsgi_context():
    from blues import uwsgi
    project_name = blueprint.get('project')
    owner = debian.get_user(project_name)

    context = dict(owner)  # name, uid, gid, ...

    # Memory optimized options
    cpu_count = blueprint.get('wsgi.max_cores', debian.nproc())
    total_memory = blueprint.get('wsgi.max_memory',
                                 default=debian.total_memory() / 1024 / 1024 / 1024)
    workers = blueprint.get('wsgi.workers', default=uwsgi.get_worker_count(cpu_count))
    gevent = blueprint.get('wsgi.gevent', default=0)

    info('Generating uWSGI conf based on {} core(s), {} GB memory and {} worker(s)',
         cpu_count, total_memory, workers)

    # TODO: Handle different loop engines (gevent)
    context.update({
        'cpu_affinity': uwsgi.get_cpu_affinity(cpu_count, workers),
        'workers': workers,
        'max_requests': int(uwsgi.get_max_requests(total_memory)),
        'reload_on_as': int(uwsgi.get_reload_on_as(total_memory)),
        'reload_on_rss': int(uwsgi.get_reload_on_rss(total_memory)),
        'limit_as': int(uwsgi.get_limit_as(total_memory)),
        'source': os.path.join(git_path(), 'src'),
        'virtualenv': virtualenv_path(),
        'gevent': gevent,
    })

    # Override defaults
    context.update(blueprint.get('wsgi'))

    return context


def upload_uwsgi_wsgi_conf(destination, context=None):
    project_name = blueprint.get('project')

    ini = '{}.ini'.format(project_name)
    template = os.path.join('uwsgi', ini)
    updates = []
    # Check if a specific web vassal have been created or use the default
    if template not in blueprint.get_template_loader().list_templates():
        # Upload default web vassal
        info(indent('...using default web vassal'))
        template = os.path.join('uwsgi', 'default', 'web.ini')
        uploads = blueprint.upload(template, os.path.join(destination, ini), context=context)
        if uploads:
            updates.extend(uploads)

    return updates


def upload_uwsgi_celery_conf(destination):
    updates = []

    if not destination.endswith(os.path.sep):
        destination = destination + os.path.sep

    project_name = blueprint.get('project')
    owner = debian.get_user(project_name)
    context = dict(owner)  # name, uid, gid, ...

    context.update({
        'workers': blueprint.get('celery.workers', debian.nproc()),
        'source': os.path.join(git_path(), 'src'),
        'virtualenv': virtualenv_path(),
    })

    # Override defaults
    context.update(blueprint.get('celery'))

    # Upload vassals
    for vassal in ('celery.ini', 'beat.ini', 'flower.ini'):
        template = os.path.join('uwsgi', 'default', vassal)
        uploads = blueprint.upload(template, destination, context=context)
        updates.extend(uploads)

    return updates


@task
def generate_nginx_conf(role='www'):
    name = blueprint.get('project')
    socket = blueprint.get('wsgi.socket', default='0.0.0.0:3030')
    host, _, port = socket.partition(':')
    if port:
        sockets = ['{}:{}'.format(host, port) for host in env.hosts]
    else:
        sockets = ['unix:{}'.format(socket)]

    context = {
        'name': name,
        'sockets': sockets,
        'domain': blueprint.get('wsgi.domain', default='_'),
        'ssl': blueprint.get('wsgi.ssl', False),
        'ip_hash': blueprint.get('wsgi.ip_hash', False)
    }
    template = 'nginx/site.conf'
    daemon = blueprint.get('wsgi.daemon')
    if daemon and daemon == 'uwsgi':
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
            python.pip('install', '-r {} --log={}'.format(requirements_path, pip_log_path))


def git_path():
    repository = git.get_repository_name(blueprint.get('git_url'))
    return os.path.join(source_path(), repository)


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
