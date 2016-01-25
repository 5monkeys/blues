import os

from fabric.context_managers import settings
from fabric.state import env
from fabric.utils import indent, warn

from refabric.api import run, info
from refabric.context_managers import sudo, silent

from .base import ManagedProvider
from ..project import *

from ... import debian
from ...app import blueprint


class UWSGIProvider(ManagedProvider):
    name = 'uwsgi'
    default_manager = 'noop'

    def install(self):
        """
        Install system wide uWSGI and upstart service.
        """
        from blues import uwsgi
        uwsgi.setup()

    def get_config_path(self):
        """
        Get or create uWSGI project vassals home dir.

        :return: Remote config path
        """
        from blues import uwsgi

        destination = uwsgi.blueprint.get('emperor')

        if destination and '*' in destination:
            # Destination can not be wildcard based
            warn('uWsgi emperor vassals dir contains wildcard, skipping')
            destination = None

        if not destination:
            # Join config path and make sure that it ends with a slash
            destination = os.path.join(project_home(), 'uwsgi.d', '')

        with sudo('root'):
            # Ensure destination exists
            debian.mkdir(destination)

        return destination

    def get_context(self):
        """
        Build jinja context for web.ini vassal.

        :return: context
        """
        from blues import uwsgi

        context = super(UWSGIProvider, self).get_context()

        # Memory optimized options
        cpu_count = blueprint.get('web.max_cores', debian.nproc())
        total_memory = int(round(debian.total_memory() / 1024.0 / 1024.0 / 1024.0))
        total_memory = blueprint.get('web.max_memory', default=total_memory)
        workers = blueprint.get('web.workers', default=uwsgi.get_worker_count(cpu_count))
        gevent = blueprint.get('web.gevent', default=0)
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
            'gevent': gevent,
            'http': blueprint.get('web.http') == 'true',
        })

        # Override context defaults with blueprint settings
        context.update(blueprint.get('web'))

        return context

    def configure_web(self):
        """
        Render and upload web.ini vassal to <project>.ini.

        :return: Updated vassals
        """
        from blues import uwsgi

        destination = self.get_config_path()
        context = self.get_context()

        ini = self.get_web_vassal()
        template = os.path.join('uwsgi', ini)

        default_templates = uwsgi.blueprint.get_default_template_root()
        with settings(template_dirs=[default_templates]):
            # Check if a specific web vassal have been created or use the default
            if template not in blueprint.get_template_loader().list_templates():
                # Upload default web vassal
                info(indent('...using default web vassal'))
                template = os.path.join('uwsgi', 'default', 'web.ini')
                uploads = blueprint.upload(template, os.path.join(destination, ini), context=context)
                if uploads:
                    self.updates.extend(uploads)

            # Upload remaining (local) vassals
            user_vassals = blueprint.upload('uwsgi/', destination, context=context)  # TODO: skip subdirs
            if user_vassals:
                self.updates.extend(user_vassals)

        return self.updates

    def configure_worker(self):
        """
        Render and upload worker vassal(s) to projects uWSGI home dir.

        :return: Updated vassals
        """
        from blues import uwsgi

        # TODO: destination could be global (uwsgi.emperor setting) and therefore contain same vassal names (celery.ini)
        destination = self.get_config_path()
        context = super(UWSGIProvider, self).get_context()
        context.update({
            'workers': blueprint.get('worker.workers', debian.nproc()),
            'queues': blueprint.get('worker.queues'),
        })

        # Override context defaults with blueprint settings
        context.update(blueprint.get('worker'))

        # Upload vassals
        for vassal in self.list_worker_vassals():
            template = os.path.join('uwsgi', 'default', vassal)
            default_templates = uwsgi.blueprint.get_default_template_root()
            with settings(template_dirs=[default_templates]):
                uploads = blueprint.upload(template, destination, context=context)
            self.updates.extend(uploads)

        return self.updates

    def get_web_vassal(self):
        """
        Return file name for web vassal

        :return: [project_name].ini
        """
        if not blueprint.get('web.provider') == 'uwsgi':
            return None

        host = env.host_string
        web_hosts = blueprint.get('web', {}).get('hosts', [])

        if not web_hosts or host in web_hosts:
            return '{}.ini'.format(blueprint.get('web.name', self.project))

    def list_worker_vassals(self):
        """
        List all valid worker vassals for current host

        :return: Set of vassal.ini file names
        """
        vassals = set()

        if not blueprint.get('worker.provider') == 'uwsgi':
            return vassals

        host = env.host_string
        worker_hosts = blueprint.get('worker', {}).get('hosts', [])

        if not worker_hosts or host in worker_hosts:
            vassals.add('celery.ini')

            # Filter vassal extensions by host
            extensions = blueprint.get('worker.extensions')
            if isinstance(extensions, list):
                # Filter of bad values
                extensions = [extension for extension in extensions if extension]
                for extension in extensions:
                    vassals.add('{}.ini'.format(extension))
            elif isinstance(extensions, dict):
                for extension, extension_host in extensions.items():
                    if extension_host in ('*', host):
                        vassals.add('{}.ini'.format(extension))

        return vassals

    def list_vassals(self):
        """
        List all valid vassals for current host

        :return: Set of vassal.ini file names
        """
        vassals = self.list_worker_vassals()
        web_vassal = self.get_web_vassal()
        if web_vassal:
            vassals.add(web_vassal)

        return vassals

    def reload(self, vassals=None):
        """
        Touch reload specified vassals

        :param vassals: Vassals to reload
        """
        from blues import uwsgi

        for vassal_ini in vassals or self.list_vassals():
            vassal_ini_path = os.path.join(self.get_config_path(), vassal_ini)
            uwsgi.reload(vassal_ini_path)
