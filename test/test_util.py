import utils
import os
import unittest

TOPDIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
utils.set_search_paths(TOPDIR)
import ihm.util

class Tests(unittest.TestCase):
    def test_asym_ids(self):
        """Test _AsymIDs class"""
        c = ihm.util._AsymIDs()
        self.assertEqual([c[i] for i in range(0, 4)],
                         ['A', 'B', 'C', 'D'])
        self.assertEqual([c[i] for i in range(24,28)],
                         ['Y', 'Z', 'AA', 'AB'])
        self.assertEqual([c[i] for i in range(50,54)],
                         ['AY', 'AZ', 'BA', 'BB'])
        self.assertEqual([c[i] for i in range(700,704)],
                         ['ZY', 'ZZ', 'AAA', 'AAB'])


if __name__ == '__main__':
    unittest.main()
