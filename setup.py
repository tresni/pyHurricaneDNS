#! /usr/bin/env python

try:
    from setuptools import setup
except ImportError:
    from distutils.core import setup

setup(name='hurricanedns',
      version='1.0',
      description='Hurricane Electric DNS python library',
      author='Brian Hartvigsen',
      author_email='brian.andrew@brianandjenny.com',
      url='https://github.com/tresni/pyhurricanedns',
      install_requires=['lxml', 'html5lib'],
      extras_require={'import': ["dnspython"]},
      py_modules=['HurricaneDNS'],
      scripts=['hurricanedns'])
