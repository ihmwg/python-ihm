import os
import sys
import tempfile
import contextlib
import shutil

def set_search_paths(topdir):
    """Set search paths so that we can import Python modules"""
    os.environ['PYTHONPATH'] = topdir + ':' + os.environ.get('PYTHONPATH', '')
    sys.path.append(topdir)

@contextlib.contextmanager
def temporary_directory():
    _tmpdir = tempfile.mkdtemp()
    yield _tmpdir
    shutil.rmtree(_tmpdir, ignore_errors=True)
