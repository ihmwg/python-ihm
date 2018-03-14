import utils
import os
import unittest
import sys

TOPDIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
utils.set_search_paths(TOPDIR)
import ihm.restraint

class Tests(unittest.TestCase):

    def test_restraint(self):
        """Test Restraint base class"""
        r = ihm.restraint.Restraint() # does nothing

    def test_em3d_restraint_fit(self):
        """Test EM3DRestraintFit class"""
        f = ihm.restraint.EM3DRestraintFit(0.4)
        self.assertAlmostEqual(f.cross_correlation_coefficient, 0.4, places=1)

    def test_em3d_restraint(self):
        """Test EM3DRestraint class"""
        f = ihm.restraint.EM3DRestraint(dataset='foo', assembly='bar')
        self.assertEqual(f.dataset, 'foo')
        self.assertEqual(f.assembly, 'bar')
        self.assertEqual(f.fits, {})


if __name__ == '__main__':
    unittest.main()
