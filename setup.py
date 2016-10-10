# -*- coding: utf-8 -*-
from ldtools import __version__, url, author_email

import os
from setuptools import setup

README = open(os.path.join(os.path.dirname(__file__), "README.rst")).read()

setup(
    name='Ldtools',
    version=__version__,
    url=url,
    license='BSD',
    author='Daniel Rech',
    author_email=author_email,
    description='A lightweight ORM for Linked Data: Consume Linked Data resources, modify the graph and write the changes back to their original source',
    long_description=README,
    packages=["ldtools"],
    entry_points={
        'console_scripts': [
            'ldtools = ldtools.cli:main'
        ]
    },

    install_requires=[
        "rdflib",
        "argparse",
        "six"
    ],

    extras_require={
        'test': [
            "nose>=1.1",
        ],
    },
    test_suite='nose.collector',

    classifiers=[
        'Development Status :: 4 - Beta',
        'Environment :: Web Environment',
        'Intended Audience :: Developers',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Programming Language :: Python :: 2.6',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3.3',
        'Programming Language :: Python :: 3.4',
        'Programming Language :: Python :: 3.5',
        'License :: OSI Approved :: BSD License',
    ],
)
