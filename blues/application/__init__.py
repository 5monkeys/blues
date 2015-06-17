from .managers import list_managers
from .providers import list_providers


def resolve_runners(name):
    """
    Get provider instance by name.

    :param name: Provider name (blueprint)
    :return: <provider>
    """

    provider, _, manager = name.partition(':')

    # LEGACY
    if provider == 'supervisor':
        provider = 'celery'
        manager = 'supervisor'
    # END LEGACY

    providers = {p.name: p for p in list_providers()}

    try:
        Provider = providers[provider]
        return Provider(manager=manager or None)
    except KeyError:
        raise NotImplementedError('"{}" is not a valid application provider'.format(name))

