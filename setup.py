#!/usr/bin/env python

from distutils.core import setup, Extension
import sys

copy_args = sys.argv[1:]

# Allow building without the C extension
build_ext = True
if '--without-ext' in copy_args:
    build_ext = False
    copy_args.remove('--without-ext')

if build_ext:
    mod = [Extension("ihm._format",
                     sources=["src/ihm_format.c", "src/ihm_format.i"],
                     swig_opts=['-keyword', '-nodefaultctor',
                                '-nodefaultdtor', '-noproxy'])]
else:
    mod = []

setup(name='ihm',
      script_args=copy_args,
      description='Package for handling IHM mmCIF files',
      author='Ben Webb',
      author_email='ben@salilab.org',
      url='https://github.com/ihmwg/python-ihm',
      ext_modules=mod,
      packages=['ihm'])
