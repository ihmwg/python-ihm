import os
import sys

def set_search_paths(topdir):
    """Set search paths so that we can import Python modules"""
    os.environ['PYTHONPATH'] = topdir + ':' + os.environ.get('PYTHONPATH', '')
    sys.path.append(topdir)
