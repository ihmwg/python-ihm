import utils
import os
import unittest

TOPDIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
utils.set_search_paths(TOPDIR)
import ihm.protocol


class Tests(unittest.TestCase):

    def test_step(self):
        """Test protocol Step class"""
        s = ihm.protocol.Step(assembly='foo', dataset_group='bar',
                              method='baz', num_models_begin=0,
                              num_models_end=42)
        self.assertIsNone(s.name)
        self.assertEqual(s.method, 'baz')
        self.assertEqual(s._get_report(), 'Unnamed step (baz) (0->42 models)')

    def test_protocol(self):
        """Test Protocol class"""
        s = ihm.protocol.Protocol(name='foo')
        self.assertEqual(s.name, 'foo')
        self.assertEqual(s.steps, [])
        self.assertEqual(s.analyses, [])


if __name__ == '__main__':
    unittest.main()
