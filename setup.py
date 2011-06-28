import os
from setuptools import setup, find_packages
from ldtools import __version__

f = open(os.path.join(os.path.dirname(__file__), 'README.rst'))
readme = f.read()
f.close()

setup(
    name='Ldtools',
    version=__version__,
    url='http://github.com/dmr/ldtools/',
    license='BSD',
    author='Daniel Rech',
    author_email='daniel@nwebs.de',
    description='A lightweight orm for Linked Data',
    long_description=readme,
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
    setup_requires = ['rdflib'],
    test_requires = ['nose'],
    test_suite = 'nose.collector',
)
