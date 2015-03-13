from contextlib import contextmanager, nested


@contextmanager
def maybe_managed(*context_managers):
    if any(map(lambda x: x is not None, context_managers)):
        with nested(*context_managers):
            yield
    else:
        yield

