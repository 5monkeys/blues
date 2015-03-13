def get_manager(name):
    managers = {m.name: m for m in list_managers()}

    try:
        return managers[name]
    except KeyError:
        raise NotImplementedError('"{}" is not a valid manager'.format(name))


def list_managers():
    from .nginx import NginxManager
    from .supervisor import SupervisorManager

    return [
        NginxManager,
        SupervisorManager
    ]