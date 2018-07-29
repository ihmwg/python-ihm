import os
import sys
import tempfile
import contextlib
import shutil
import distutils.util

def set_search_paths(topdir):
    """Set search paths so that we can import Python modules"""
    platform = distutils.util.get_platform()
    distutils_dirs = (os.path.join(topdir, 'build',
                                   "lib.%s-%d.%d" % (platform,
                                                     sys.version_info[0],
                                                     sys.version_info[1])),
                      os.path.join(topdir, 'build', 'lib'))

    for d in distutils_dirs:
        if os.path.exists(d):
            os.environ['PYTHONPATH'] = d + os.pathsep \
                                       + os.environ.get('PYTHONPATH', '')
            sys.path.insert(0, d)
            return

    raise ValueError("Could not find distutils build directories %s. "
                     "Run 'setup.py build' in the toplevel directory "
                     "first." % ", ".join(distutils_dirs))

def get_input_file_name(topdir, fname):
    """Return full path to a test input file"""
    return os.path.join(topdir, 'test', 'input', fname)

@contextlib.contextmanager
def temporary_directory(dir=None):
    _tmpdir = tempfile.mkdtemp(dir=dir)
    yield _tmpdir
    shutil.rmtree(_tmpdir, ignore_errors=True)

if 'coverage' in sys.modules:
    import atexit
    # Collect coverage information from subprocesses
    __site_tmpdir = tempfile.mkdtemp()
    with open(os.path.join(__site_tmpdir, 'sitecustomize.py'), 'w') as fh:
        fh.write("""
import coverage
import atexit
import os

_cov = coverage.coverage(branch=True, data_suffix=True, auto_data=True,
                         data_file=os.path.join('%s', '.coverage'))
_cov.start()

def _coverage_cleanup(c):
    c.stop()
atexit.register(_coverage_cleanup, _cov)
""" % os.getcwd())

    os.environ['PYTHONPATH'] = __site_tmpdir + os.pathsep \
                               + os.environ.get('PYTHONPATH', '')

    def __cleanup(d):
        shutil.rmtree(d, ignore_errors=True)
    atexit.register(__cleanup, __site_tmpdir)
