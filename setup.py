#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""The setup script."""

from setuptools import setup, find_packages

# with open('README.rst') as readme_file:
#     readme = readme_file.read()
#
# with open('HISTORY.rst') as history_file:
#     history = history_file.read()

requirements = [
    'Click>=6.0',
    'python-telegram-bot==6.1.0',
    'pymongo',
    'pendulum>=1.2.4',
    'requests>=2.18.1',
    'geocoder>=1.23.2',
    'numpy>=1.13.3',
    's2sphere>=0.2.5',
    'Flask>=1.0.2',
    'geopy',
    'protobuf',
]

setup_requirements = [
    # TODO(exiva): put setup requirements (distutils extensions, etc.) here
]

test_requirements = [
    # TODO: put package test requirements here
]

setup(
    name='poGoRaidBot',
    version='0.0.1',
    description="Python Boilerplate contains all the boilerplate you need to create a Python package.",
    long_description="idk.",
    author="Travis La Marr",
    author_email='travis@lamarr.me',
    url='https://github.com/exiva/poGoRaidBot',
    packages=find_packages(include=['poGoRaidBot']),
    entry_points={
        'console_scripts': [
            'poGoRaidBot=poGoRaidBot.cli:cli'
        ]
    },
    include_package_data=True,
    install_requires=requirements,
    dependency_links=[],
    license="MIT license",
    zip_safe=False,
    keywords='poGoRaidBot',
    classifiers=[
        'Development Status :: 2 - Pre-Alpha',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: MIT License',
        'Natural Language :: English',
        "Programming Language :: Python :: 2",
        'Programming Language :: Python :: 2.6',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.3',
        'Programming Language :: Python :: 3.4',
        'Programming Language :: Python :: 3.5',
    ],
    test_suite='tests',
    tests_require=test_requirements,
    setup_requires=setup_requirements,
)
