import utils
import os
import unittest
import sys

TOPDIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
utils.set_search_paths(TOPDIR)
import ihm.model

class Tests(unittest.TestCase):

    def test_model(self):
        """Test Model class"""
        m = ihm.model.Model(assembly='foo', protocol='bar',
                            representation='baz')
        self.assertEqual(m.name, None)
        self.assertEqual(m.protocol, 'bar')

    def test_model_group(self):
        """Test ModelGroup class"""
        m = ihm.model.Model(assembly='foo', protocol='bar',
                            representation='baz')
        g = ihm.model.ModelGroup([m], name='foo')
        self.assertEqual(g.name, 'foo')
        self.assertEqual(g[0].protocol, 'bar')


if __name__ == '__main__':
    unittest.main()
