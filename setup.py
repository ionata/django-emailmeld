#!/usr/bin/env python
from __future__ import absolute_import, print_function

import io

from setuptools import setup, find_packages


def _read(filename):
    with io.open(filename, encoding='utf-8') as handle:
        return handle.read()


setup(
    name='django-emailmeld',
    version='0.0.6',
    description='Django Email Templater.',
    long_description=_read('README.md') + _read('AUTHORS.rst') + _read('CHANGELOG.rst'),
    author='Ionata Digital',
    author_email='spam@ionata.com.au',
    url='https://github.com/ionata/django-emailmeld',
    packages = find_packages(exclude=['project',]),
    install_requires=['markdown'],
    include_package_data=True,
    classifiers=[
        'Environment :: Web Environment',
        'Framework :: Django',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: BSD License',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Programming Language :: Python :: 2',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.5',
        'Programming Language :: Python :: 3.6',
        "Development Status :: 4 - Beta",
        "Topic :: Internet :: WWW/HTTP :: Dynamic Content",
    ],
)
