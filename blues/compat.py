import pip


pip_version = tuple(int(v) if v.isdigit() else v
                    for v in pip.__version__.split('.'))

if pip_version > (10,):
    from pip._internal.req import req_file
else:
    from pip.req import req_file


def req_file_build_parser(line=None):
    if pip_version > (10,):
        return req_file.build_parser(line=line)
    else:
        return req_file.build_parser()


__all__ = [
    'pip_version',
    'req_file',
    'req_file_build_parser',
]
