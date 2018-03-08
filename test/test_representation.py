import utils
import os
import unittest

TOPDIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
utils.set_search_paths(TOPDIR)
import ihm.representation

class Tests(unittest.TestCase):

    def test_segment(self):
        """Test Segment base class"""
        s = ihm.representation.Segment() # does nothing

    def test_atomic_segment(self):
        """Test AtomicSegment class"""
        s = ihm.representation.AtomicSegment(
                asym_unit='foo', seq_id_range=(1,10),
                rigid=True, starting_model=None)
        self.assertEqual(s.primitive, 'atomistic')
        self.assertEqual(s.granularity, 'by-atom')
        self.assertEqual(s.count, None)
        self.assertEqual(s.rigid, True)

    def test_residue_segment(self):
        """Test ResidueSegment class"""
        s = ihm.representation.ResidueSegment(
                asym_unit='foo', seq_id_range=(1,10),
                rigid=True, primitive='sphere')
        self.assertEqual(s.primitive, 'sphere')
        self.assertEqual(s.granularity, 'by-residue')
        self.assertEqual(s.count, None)
        self.assertEqual(s.rigid, True)

    def test_multi_residue_segment(self):
        """Test MultiResidueSegment class"""
        s = ihm.representation.MultiResidueSegment(
                asym_unit='foo', seq_id_range=(1,10),
                rigid=True, primitive='sphere')
        self.assertEqual(s.primitive, 'sphere')
        self.assertEqual(s.granularity, 'multi-residue')
        self.assertEqual(s.count, None)
        self.assertEqual(s.rigid, True)

    def test_feature_segment(self):
        """Test FeatureSegment class"""
        s = ihm.representation.FeatureSegment(
                asym_unit='foo', seq_id_range=(1,10),
                rigid=True, primitive='sphere', count=4)
        self.assertEqual(s.primitive, 'sphere')
        self.assertEqual(s.granularity, 'by-feature')
        self.assertEqual(s.count, 4)
        self.assertEqual(s.rigid, True)

    def test_representation(self):
        """Test Representation class"""
        s = ihm.representation.AtomicSegment(
                            asym_unit='foo', seq_id_range=(1,10), rigid=True)
        r = ihm.representation.Representation()
        r.append(s)
        self.assertEqual(len(r), 1)


if __name__ == '__main__':
    unittest.main()
