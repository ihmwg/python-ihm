import os
import sys
import tempfile
import contextlib
import sysconfig
import shutil

def set_search_paths(topdir):
    """Set search paths so that we can import Python modules"""
    distutils_dir = os.path.join(topdir, 'build',
                                 "lib.%s-%d.%d" % (sysconfig.get_platform(),
                                                   sys.version_info[0],
                                                   sys.version_info[1]))
    if not os.path.exists(distutils_dir):
        raise ValueError("Could not find distutils build directory %s. "
                         "Run 'setup.py build' in the toplevel directory "
                         "first." % distutils_dir)
    os.environ['PYTHONPATH'] = distutils_dir + os.pathsep \
                               + os.environ.get('PYTHONPATH', '')
    sys.path.insert(0, distutils_dir)

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
