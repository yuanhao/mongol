#!/usr/bin/env python

import sys
import os
# try:
    # import subprocess
    # has_subprocess = True
# except:
    # has_subprocess = False
import shutil

# from ez_setup import use_setuptools
# use_setuptools()

from setuptools import setup
from setuptools import Feature
from distutils.cmd import Command
from distutils.command.build_ext import build_ext
from distutils.errors import CCompilerError
from distutils.errors import DistutilsPlatformError, DistutilsExecError
from distutils.core import Extension

requirements = ['pymongo']

# f = open('README.rst')
# try:
    # try:
        # readme_content = f.read()
    # except:
        # readme_content = ''
# finally:
    # f.close()

readme_content = ''

# class GenerateDoc(Command):
    # user_options = []

    # def initialize_options(self):
        # pass

    # def finalize_options(self):
        # pass

    # def run(self):
        # path = 'doc/%s' % version

        # shutil.rmtree('doc', ignore_errors=True)
        # os.makedirs(path)

        # if has_subprocess:
            # subprocess.call(['epydoc', '--config', 'epydoc-config', '-o', path])
        # else:
            # print """
# `setup.py doc` is not supported for this version of Python.

# Please ask in the user forums for help.
# """


setup(
    name = 'mongol',
    version = '0.1.0',
    description = 'A lightweight Object Document Mapper for PyMongo and MongoDB <http://www.mongodb.org>',
    long_description = readme_content,
    author = 'Yuanhao Li',
    author_email = 'yuanhao.li [at] gmail [dot] com',
    url = 'https://github.com/yuanhao/mongol/',
    packages = ['mongol', ],
    install_requires = requirements,
    license = 'New BSD License',
    test_suite = 'tests',
    classifiers = [
        'Development Status :: 4 - Beta',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: BSD License',
        'Operating System :: MacOS :: MacOS X',
        'Operating System :: Microsoft :: Windows',
        'Operating System :: POSIX',
        'Programming Language :: Python',
        'Topic :: Database'],
    # cmdclass = {'doc': GenerateDoc},
)


