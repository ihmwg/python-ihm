import os
import sys
import tempfile
import contextlib
import shutil

def set_search_paths(topdir):
    """Set search paths so that we can import Python modules"""
    os.environ['PYTHONPATH'] = topdir + ':' + os.environ.get('PYTHONPATH', '')
    sys.path.append(topdir)

def get_input_file_name(topdir, fname):
    """Return full path to a test input file"""
    return os.path.join(topdir, 'test', 'input', fname)

@contextlib.contextmanager
def temporary_directory(dir=None):
    _tmpdir = tempfile.mkdtemp(dir=dir)
    yield _tmpdir
    shutil.rmtree(_tmpdir, ignore_errors=True)
