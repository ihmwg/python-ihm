import utils
import os
import unittest
import sys
if sys.version_info[0] >= 3:
    from io import StringIO
else:
    from io import BytesIO as StringIO

TOPDIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
utils.set_search_paths(TOPDIR)
import ihm

class Tests(unittest.TestCase):
    def test_system(self):
        """Test System class"""
        s = ihm.System('test system')
        self.assertEqual(s.name, 'test system')


if __name__ == '__main__':
    unittest.main()
