# -*- coding: utf-8 -*-
__version__ = "0.5.5"

import os
from setuptools import setup, find_packages

README = open(os.path.join(os.path.dirname(__file__), "README.rst")).read()

setup(
    name='Ldtools',
    version=__version__,
    url='http://github.com/dmr/ldtools/',
    license='BSD',
    author='Daniel Rech',
    author_email='daniel@nwebs.de',
    description='A lightweight orm for Linked Data',
    long_description=README,
    packages=find_packages(),

    scripts=['scripts/ldtools'],

    install_requires=[
        "rdflib",
        "argparse",
    ],

    extras_require={
        'tests': ["nose", "unittest2",],
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
