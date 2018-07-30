[![docs](https://readthedocs.org/projects/python-ihm/badge/)](https://python-ihm.readthedocs.org/)
[![Linux Build Status](https://travis-ci.org/ihmwg/python-ihm.svg?branch=master)](https://travis-ci.org/ihmwg/python-ihm)
[![Windows Build Status](https://ci.appveyor.com/api/projects/status/5o28oe477ii8ur4h?svg=true)](https://ci.appveyor.com/project/benmwebb/python-ihm)
[![codecov](https://codecov.io/gh/ihmwg/python-ihm/branch/master/graph/badge.svg)](https://codecov.io/gh/ihmwg/python-ihm)

This is a Python package to assist in handling mmCIF files compliant
with the integrative/hybrid modeling (IHM) extension. It works with Python 2.6
or later (Python 3 is fully supported).

Please [see the documentation](https://python-ihm.readthedocs.org/)
or some [worked examples](examples) for more details.

# Installation

To build and install, run

```
python setup.py build
python setup.py install
```

Note that a C extension module is built for faster parsing of mmCIF files.
This requires that your system has a C compiler, the
[GLib](https://developer.gnome.org/glib/stable/glib.html) library,
[pkg-config](https://www.freedesktop.org/wiki/Software/pkg-config/),
and [SWIG](http://www.swig.org/). If any of these components are missing, you
can choose to build without the extension by adding `--without-ext` to both
`setup.py` command lines above.
