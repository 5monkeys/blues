import os

from fabric.utils import abort
from fabric.contrib import files
from fabric.decorators import task
from fabric.context_managers import cd

from refabric.context_managers import sudo, silent
from refabric.contrib import blueprints
from refabric.api import run, info

from . import debian

build_deps = 'unzip cmake git libgtk2.0-dev pkg-config libavcodec-dev ' \
             'libavformat-dev libswscale-dev'.split()

build_deps_optional = 'libtbb2 libtbb-dev libjpeg-dev libpng-dev libtiff-dev' \
                      ' libjasper-dev libdc1394-22-dev'.split()

zip_url_template = 'http://downloads.sourceforge.net/project/opencvlibrary' \
               '/opencv-unix/{version}/opencv-{version}.zip'
python_library_template = '/usr/lib/x86_64-linux-gnu/libpython{version}m.so'
python_include_template = '{venv}/include/python{version}m'
numpy_includes_template = '{venv}/lib/python{version}/site-packages' \
                          '/numpy/core/include'
python_packages_path_template = '{venv}/lib/python{version}/site-packages'


blueprint = blueprints.get(__name__)

python_executable = blueprint.get('python_executable')
python_version = blueprint.get('python_version')
user = blueprint.get('user')
version = blueprint.get('version')


@task
def setup():
    """
    Compile and install OpenCV.
    """
    install_from_source(version, python_executable, python_version, user)


def install_from_source(version, python_executable, python_version, user):
    if not version:
        raise ValueError('No version specified for opencv')

    release_build_path = setup_build_environment(version, user)

    # Set up build options

    venv_path = os.path.abspath(
        os.path.join(
            os.path.dirname(python_executable),
            '..',
        )
    )
    install_prefix = venv_path
    python_include_dir = python_include_template.format(venv=venv_path,
                                                        version=python_version)

    python_library = python_library_template.format(version=python_version)

    numpy_include_dirs = numpy_includes_template.format(
        venv=venv_path,
        version=python_version
    )
    python_packages_path = python_packages_path_template.format(
        venv=venv_path,
        version=python_version
    )

    cmake_opts = {
        'CMAKE_BUILD_TYPE': 'RELEASE',
        'CMAKE_INSTALL_PREFIX': install_prefix,
        # Apparently you don't need these if you just activate the
        # virtualenv first.
        #'PYTHON3_INCLUDE_DIR': python_include_dir,
        #'PYTHON3_INCLUDE_DIRS': python_include_dir,
        #'PYTHON3_EXECUTABLE': python_executable,
        #'PYTHON3_LIBRARIES': python_library,
        #'PYTHON3_NUMPY_INCLUDE_DIRS': numpy_include_dirs,
        #'PYTHON3_PACKAGES_PATH': python_packages_path,
    }

    with cd(release_build_path), sudo(user):
        info('Running cmake...')
        opts = ' '.join('-D {}={}'.format(key, value)
                        for key, value in cmake_opts.items())
        cmake = run('source {activate} && cmake {opts} ..'.format(
            activate=os.path.join(venv_path, 'bin', 'activate'),
            opts=opts
        ), shell=True)
        if cmake.return_code:
            abort('cmake failed with exit code {}'.format(
                cmake.return_code))

        info('Running make')
        make = run('make -j')
        if make.return_code:
            abort('make failed with exit code {}'.format(
                make.return_code
            ))

        info('Installing OpenCV into {}', install_prefix)

        make_install = run('make install')
        if make_install.return_code:
            abort('make install failed with exit code {}'.format(
                make_install.return_code))


def setup_build_environment(version, user):
    """
    Create source directories, download OpenCV source zip and extract.
    """
    with sudo():
        debian.apt_get_update()
        debian.apt_get('install', *(build_deps + build_deps_optional))

    source_base = '/usr/src/opencv-{version}'.format(version=version)
    with sudo():
        debian.mkdir(source_base, owner=user)

    with sudo(user):
        with cd(source_base):
            zip_url = zip_url_template.format(version=version)
            zip_file = 'opencv-{}.zip'.format(version)

            if files.exists(zip_file):
                info('Found existing zip file {}', zip_file)
            else:
                info('Fetching OpenCV {} source from {}', version, zip_url)
                run('curl -L {zip_url} > {zip_file}'.format(
                    zip_url=zip_url,
                    zip_file=zip_file))

            run('unzip -u {}'.format(zip_file))

        source_path = os.path.join(source_base, 'opencv-{}'.format(version))

        release_build_path = os.path.join(source_path, 'release')
        if files.exists(release_build_path):
            # Be stupidly paranoid
            assert ' ' not in release_build_path
            assert len(release_build_path) > 3, 'Too scary'
            debian.rm(release_build_path, recursive=True)

        debian.mkdir(release_build_path)

    return release_build_path
