# -*- coding: utf-8 -*-
__version__ = "0.4.3"

import os
from setuptools import setup, find_packages

def read_file(file_name):
    file_name = os.path.join(os.path.dirname(__file__), file_name)
    with open(file_name, "r") as f:
        content = f.read()
    return content

setup(
    name='Ldtools',
    version=__version__,
    url='http://github.com/dmr/ldtools/',
    license='BSD',
    author='Daniel Rech',
    author_email='daniel@nwebs.de',
    description='A lightweight orm for Linked Data',
    long_description=read_file("README.rst"),
    packages=find_packages(),

    install_requires=["rdflib"],

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
