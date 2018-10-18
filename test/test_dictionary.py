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
import ihm.dictionary

class Tests(unittest.TestCase):
    def test_read(self):
        """Test read() function"""
        cif = """
save_foo
  _category.id               test_category1
  _category.mandatory_code   yes
save_

save_bar
  _item.name                 'test_category1.bar'
  _item.category_id          test_category1
  _item.mandatory_code       no
save_

save_baz
  _item.name                 'test_category2.baz'
  _item.category_id          test_category2
  _item.mandatory_code       no
save_
"""
        d = ihm.dictionary.read(StringIO(cif))
        self.assertEqual(sorted(d.categories.keys()),
                         ['test_category1', 'test_category2'])
        c1 = d.categories['test_category1']
        self.assertTrue(c1.mandatory)
        self.assertEqual(sorted(c1.keywords.keys()), ["bar"])
        self.assertFalse(c1.keywords['bar'].mandatory)
        c2 = d.categories['test_category2']
        self.assertEqual(c2.mandatory, None)
        self.assertEqual(sorted(c2.keywords.keys()), ["baz"])
        self.assertFalse(c2.keywords['baz'].mandatory)

if __name__ == '__main__':
    unittest.main()
