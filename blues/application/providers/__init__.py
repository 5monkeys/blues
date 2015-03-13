from refabric.contrib import blueprints

blueprint = blueprints.get('app')


def list_providers():
    from .celery import CeleryProvider
    from .uwsgi import UWSGIProvider
    from .node import NodeProvider
    from .gunicorn import GunicornProvider
    from .program import ProgramProvider

    return [
        CeleryProvider,
        UWSGIProvider,
        NodeProvider,
        GunicornProvider,
        ProgramProvider
    ]


def get_providers(host=None):
    """
    Get configured web/worker providers by host.

    :param host: Provider host filter
    :return: dict(web=<provider>, worker=<provider>)
    """
    from .. import resolve_runners
    providers = {}

    # TODO: TEST! TEST! TEST! NEEDS TESTING!, rewrote host filtering.

    web_hosts = blueprint.get('web.hosts')
    # Filter out bad values
    web_hosts = filter(lambda x: x, web_hosts)
    web_provider = blueprint.get('web.provider')

    if web_provider:
        providers[web_provider] = resolve_runners(web_provider)

    # Install worker providers
    worker_hosts = blueprint.get('worker.hosts')

    # Filter out bad values
    worker_hosts = filter(lambda x: x, worker_hosts)
    worker_provider = blueprint.get('worker.provider')

    # Set special provider if
    if worker_provider and worker_provider not in providers:
        providers[worker_provider] = resolve_runners(worker_provider)

    # Set web provider if web_hosts are not set, or if current host is in
    # web.hosts
    if web_provider and (not web_hosts or host in web_hosts):
        providers['web'] = providers[web_provider]

    # Set worker provider if worker_hosts are not set, or if current host is in
    # worker.hosts
    if worker_provider and (not worker_hosts or host in worker_hosts):
        providers['worker'] = providers[worker_provider]

    # Remove provider name keys
    provider_name_keys = {worker_provider, web_provider}
    for provider_name in provider_name_keys:
        if provider_name:
            providers.pop(provider_name)

    return providers