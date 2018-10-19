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

def make_test_dictionary():
    def add_keyword(name, mandatory, category):
        k = ihm.dictionary.Keyword()
        k.name, k.mandatory = name, mandatory
        category.keywords[k.name] = k
        return k

    d = ihm.dictionary.Dictionary()

    c = ihm.dictionary.Category()
    c.name = 'test_mandatory_category'
    c.mandatory = True
    add_keyword("foo", False, c)
    k = add_keyword("bar", True, c)
    k.item_type = ihm.dictionary.ItemType('int', '[+-]?[0-9]+')
    d.categories[c.name] = c

    c = ihm.dictionary.Category()
    c.name = 'test_optional_category'
    c.mandatory = False
    add_keyword("foo", False, c)
    k = add_keyword("bar", True, c)
    k.enumeration = set(('enum1', 'enum2'))
    d.categories[c.name] = c

    return d

class Tests(unittest.TestCase):
    def test_read(self):
        """Test read() function"""
        cif = """
loop_
_item_type_list.code
_item_type_list.construct
code '[][_,.;:"&<>()/\{}'`~!@#$%A-Za-z0-9*|+-]*'

save_foo
  _category.id               test_category1
  _category.mandatory_code   yes
save_

save_bar
  _item.name                 'test_category1.bar'
  _item.category_id          test_category1
  _item.mandatory_code       no
  _item_type.code            code
save_

save_bar2
  _item.name                 'test_category1.bar2'
  _item.category_id          test_category1
  _item.mandatory_code       no
  _item_type.code            atcode
save_

save_baz
  _item.name                 'test_category2.baz'
  _item.category_id          test_category2
  _item.mandatory_code       no
  loop_
    _item_enumeration.value
    "enum 1"
    "enum 2"
save_
"""
        d = ihm.dictionary.read(StringIO(cif))
        self.assertEqual(sorted(d.categories.keys()),
                         ['test_category1', 'test_category2'])
        c1 = d.categories['test_category1']
        self.assertTrue(c1.mandatory)
        self.assertEqual(sorted(c1.keywords.keys()), ["bar", "bar2"])
        self.assertFalse(c1.keywords['bar'].mandatory)
        self.assertEqual(c1.keywords['bar'].enumeration, None)
        self.assertEqual(c1.keywords['bar'].item_type.name, "code")
        self.assertEqual(c1.keywords['bar2'].item_type, None)

        c2 = d.categories['test_category2']
        self.assertEqual(c2.mandatory, None)
        self.assertEqual(sorted(c2.keywords.keys()), ["baz"])
        self.assertFalse(c2.keywords['baz'].mandatory)
        self.assertEqual(c2.keywords['baz'].enumeration,
                         set(('enum 1', 'enum 2')))
        self.assertEqual(c2.keywords['baz'].item_type, None)

    def test_validate_ok(self):
        """Test successful validation"""
        d = make_test_dictionary()
        d.validate(StringIO("_test_mandatory_category.bar 1"))

    def test_validate_missing_mandatory_category(self):
        """Test validation failure with missing mandatory category"""
        d = make_test_dictionary()
        self.assertRaises(ihm.dictionary.ValidatorError,
                          d.validate, StringIO("_struct.entry_id id1"))

    def test_validate_missing_mandatory_keyword(self):
        """Test validation failure with missing mandatory keyword"""
        d = make_test_dictionary()
        self.assertRaises(ihm.dictionary.ValidatorError, d.validate,
                          StringIO("_test_mandatory_category.bar ?"))

    def test_validate_enumeration(self):
        """Test validation of enumerated values"""
        prefix = """_test_mandatory_category.bar 1
                    _test_optional_category.bar """
        d = make_test_dictionary()
        # Value in the enumeration is OK
        d.validate(StringIO(prefix + 'enum1'))
        # Omitted value is OK
        d.validate(StringIO(prefix + '.'))
        # Value not in the enumeration is not OK
        self.assertRaises(ihm.dictionary.ValidatorError, d.validate,
                          StringIO(prefix + 'bad'))

    def test_validate_item_type(self):
        """Test validation of item type"""
        prefix = "_test_mandatory_category.bar "
        d = make_test_dictionary()
        # Int value is OK
        d.validate(StringIO(prefix + '+45'))
        d.validate(StringIO(prefix + '-4'))
        d.validate(StringIO(prefix + '5'))
        # Omitted value is OK
        d.validate(StringIO(prefix + '.'))
        # Non-int value is not OK
        self.assertRaises(ihm.dictionary.ValidatorError, d.validate,
                          StringIO(prefix + '45A'))
        self.assertRaises(ihm.dictionary.ValidatorError, d.validate,
                          StringIO(prefix + 'foo'))
        self.assertRaises(ihm.dictionary.ValidatorError, d.validate,
                          StringIO(prefix + '++44'))
        self.assertRaises(ihm.dictionary.ValidatorError, d.validate,
                          StringIO(prefix + '44+'))


if __name__ == '__main__':
    unittest.main()