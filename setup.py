#!/usr/bin/env python
import codecs
import os
from setuptools import setup, find_packages


version = __import__('blues').__version__

setup(
    name='Blues',
    version=version,
    description='Blueprints for fabric',
    long_description=codecs.open(
        os.path.join(
            os.path.dirname(__file__),
            'README.md'
        )
    ).read(),
    author='Jonas Lundberg',
    author_email='jonas@5monkeys.se',
    url='https://github.com/5monkeys/blues',
    download_url='https://github.com/5monkeys/blues/tarball/%s' % version,
    keywords=['fabric', 'blueprints', 'deploy', 'build'],
    license='MIT',
    packages=find_packages(exclude='tests'),
    install_requires=['ghp-import'],
    include_package_data=False,
    zip_safe=False,
    classifiers=[
        'Development Status :: 5 - Production/Stable',
        'Environment :: Console',
        'Intended Audience :: Developers',
        'Intended Audience :: System Administrators',
        'License :: OSI Approved :: MIT License',
        'Operating System :: MacOS :: MacOS X',
        'Operating System :: Unix',
        'Operating System :: POSIX',
        'Programming Language :: Python',
        'Programming Language :: Python :: 2.5',
        'Programming Language :: Python :: 2.6',
        'Programming Language :: Python :: 2.7',
        'Topic :: Software Development',
        'Topic :: Software Development :: Build Tools',
        'Topic :: Software Development :: Libraries',
        'Topic :: Software Development :: Libraries :: Python Modules',
        'Topic :: System :: Clustering',
        'Topic :: System :: Software Distribution',
        'Topic :: System :: Systems Administration',
    ]
)
