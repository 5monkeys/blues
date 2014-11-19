from .uwsgi import UWSGIProvider
from .supervisor import SupervisorProvider


def get_provider(name):
    if name == 'uwsgi':
        return UWSGIProvider()
    elif name == 'supervisor':
        return SupervisorProvider()
    else:
        raise NotImplementedError('"{}" is not a valid application provider'.format(name))
