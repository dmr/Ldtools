# -*- coding: utf-8 -*-
from ldtools import __version__, url, author_email

import os
from setuptools import setup #, find_packages

README = open(os.path.join(os.path.dirname(__file__), "README.rst")).read()

setup(
    name='Ldtools',
    version=__version__,
    url=url,
    license='BSD',
    author='Daniel Rech',
    author_email=author_email,
    description='A lightweight ORM for Linked Data',
    long_description=README,

    packages=["ldtools"],
    #packages=find_packages(),

    entry_points={
        'console_scripts': [
            'ldtools = ldtools.cli:main'
        ]
    },

    install_requires=[
        "rdflib",
        "argparse",
    ],

    extras_require={
        'test': [
            "unittest2",
            "spec",
            "nose>=1.1,<1.2",
        ],
    },
    test_suite='nose.collector',

    classifiers=[
        'Development Status :: 4 - Beta',
        'Environment :: Web Environment',
        'Intended Audience :: Developers',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'License :: OSI Approved :: BSD License',
    ],
)
