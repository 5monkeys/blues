from fabric.decorators import task
from fabric.operations import prompt
from refabric.state import blueprint_settings

settings = blueprint_settings(__name__)


@task
def manage(cmd=''):
    django_settings = settings('settings')

    if django_settings:
        django_settings = '--settings={}'.format(django_settings)

    if not cmd:
        cmd = prompt('Enter django management command:')

    print 'manage.py {cmd} {settings}'.format(cmd=cmd,
                                              settings=django_settings)
    repo = settings('git')


@task
def build():
    pass
