#!/usr/bin/env python

from distutils.core import setup, Extension
import subprocess

def getoutput(args):
    return subprocess.check_output(args, universal_newlines=True)

def pkgconfig(*packages, **kw):
    """Utility function to parse pkg-config output"""
    flag_map = {'-I': 'include_dirs', '-L': 'library_dirs', '-l': 'libraries'}
    for token in getoutput(["pkg-config", "--libs",
                            "--cflags"] + list(packages)).split():
        kw.setdefault(flag_map.get(token[:2]), []).append(token[2:])
    return kw

# Get paths for glib 2.0:
glib = pkgconfig("glib-2.0")

mod = Extension("ihm._reader",
                sources=["src/reader.c", "src/reader.i"],
                include_dirs=glib['include_dirs'],
                library_dirs=glib.get('library_dirs', []),
                libraries=glib['libraries'],
                swig_opts=['-keyword', '-nodefaultctor',
                           '-nodefaultdtor', '-noproxy'])

setup(name='ihm',
      description='Package for handling IHM mmCIF files',
      author='Ben Webb',
      author_email='ben@salilab.org',
      url='https://github.com/ihmwg/python-ihm',
      ext_modules=[mod],
      packages=['ihm'])
