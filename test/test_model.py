import utils
import os
import unittest
import sys

TOPDIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
utils.set_search_paths(TOPDIR)
import ihm.model

class Tests(unittest.TestCase):

    def test_sphere(self):
        """Test Sphere class"""
        s = ihm.model.Sphere(asym_unit='foo', seq_id_range=(1,5), x=1.0,
                             y=2.0, z=3.0, radius=4.0)
        self.assertEqual(s.asym_unit, 'foo')
        self.assertEqual(s.seq_id_range, (1,5))

    def test_model(self):
        """Test Model class"""
        m = ihm.model.Model(assembly='foo', protocol='bar',
                            representation='baz')
        self.assertEqual(m.name, None)
        self.assertEqual(m.protocol, 'bar')

    def test_model_get_spheres(self):
        """Test Model.get_spheres()"""
        m = ihm.model.Model(assembly='foo', protocol='bar',
                            representation='baz')
        spheres = ['sphere1', 'sphere2']
        m._spheres = spheres[:]
        new_spheres = [s for s in m.get_spheres()]
        self.assertEqual(new_spheres, spheres)

    def test_model_set_spheres(self):
        """Test Model.set_spheres()"""
        spheres = ['sphere1', 'sphere2']
        def spheregen():
            for s in spheres:
                yield s
        m = ihm.model.Model(assembly='foo', protocol='bar',
                            representation='baz')
        m.set_spheres(spheregen())
        self.assertEqual(m._spheres, spheres)

    def test_model_group(self):
        """Test ModelGroup class"""
        m = ihm.model.Model(assembly='foo', protocol='bar',
                            representation='baz')
        g = ihm.model.ModelGroup([m], name='foo')
        self.assertEqual(g.name, 'foo')
        self.assertEqual(g[0].protocol, 'bar')


if __name__ == '__main__':
    unittest.main()
