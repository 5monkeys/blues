from .uwsgi import UWSGIProvider
from .supervisor import SupervisorProvider
from ...app import blueprint


def get_provider(name):
    """
    Get provider instance by name.

    :param name: Provider name (blueprint)
    :return: <provider>
    """
    if name == 'uwsgi':
        return UWSGIProvider()
    elif name == 'supervisor':
        return SupervisorProvider()
    else:
        raise NotImplementedError('"{}" is not a valid application provider'.format(name))


def get_providers(host=None):
    """
    Get configured web/worker providers by host.

    :param host: Provider host filter
    :return: dict(web=<provider>, worker=<provider>)
    """
    providers = {}

    web_hosts = blueprint.get('web.hosts')
    # Filter out bad values
    web_hosts = [host for host in web_hosts if host]
    web_provider = blueprint.get('web.provider')
    if web_provider:
        providers[web_provider] = get_provider(web_provider)

    worker_hosts = blueprint.get('worker.hosts')
    # Filter out bad values
    worker_hosts = [host for host in worker_hosts if host]
    worker_provider = blueprint.get('worker.provider')
    if worker_provider and worker_provider not in providers:
        providers[worker_provider] = get_provider(worker_provider)

    if web_provider and (not web_hosts or host in web_hosts):
        providers['web'] = providers[web_provider]

    if worker_provider and (not worker_hosts or host in worker_hosts):
        providers['worker'] = providers[worker_provider]

    # Remove provider name keys
    provider_name_keys = {worker_provider, web_provider}
    for provider_name in provider_name_keys:
        providers.pop(provider_name)

    return providers
