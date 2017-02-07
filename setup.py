#! /usr/bin/env python

try:
    from setuptools import setup
except ImportError:
    from distutils.core import setup

setup(name='hurricanedns',
      version='1.0.1',
      description='Hurricane Electric DNS python library',
      author='Brian Hartvigsen',
      author_email='brian.andrew@brianandjenny.com',
      url='https://github.com/tresni/pyhurricanedns',
      install_requires=['lxml', 'html5lib'],
      extras_require={'import': ["dnspython"]},
      py_modules=['HurricaneDNS'],
      scripts=['hurricanedns'],
      classifiers=[
          "Development Status :: 5 - Production/Stable",
          "Environment :: Console",
          "Intended Audience :: Information Technology",
          "Intended Audience :: System Administrators",
          "License :: OSI Approved :: MIT License",
          "Operating System :: OS Independent",
          "Programming Language :: Python",
          "Programming Language :: Python :: 2",
          "Programming Language :: Python :: 2.7",
          "Programming Language :: Python :: 3",
          "Programming Language :: Python :: 3.5",
          "Topic :: Internet :: Name Service (DNS)",
          "Topic :: Utilities"
      ])
