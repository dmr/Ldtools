# -*- coding: utf-8 -*-
__version__ = "0.4.3"

import os
from setuptools import setup, find_packages

setup(
    name='Ldtools',
    version=__version__,
    url='http://github.com/dmr/ldtools/',
    license='BSD',
    author='Daniel Rech',
    author_email='daniel@nwebs.de',
    description='A lightweight orm for Linked Data',
    long_description=("Ldtools provides a usable API for RDF data. Different "
        "backends can either publish local data on the web or use data from "
        "the web within your application."),
    py_modules=['ldtools'],
    zip_safe=False,
    platforms='any',
    classifiers=[
        'Development Status :: 4 - Beta',
        'Environment :: Web Environment',
        'Intended Audience :: Developers',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'License :: OSI Approved :: BSD License',
    ],
    install_requires=['rdflib'],
    tests_require=['nose'],
    test_suite='nose.collector',
)
