"""Classes to read in and represent an mmCIF extension dictionary"""

import ihm.reader
import ihm.format

from ihm.reader import _Handler, _get_bool

class Dictionary(object):
    """Representation of an mmCIF dictionary.
       See :func:`read` to create a Dictionary from a file."""
    def __init__(self):
        #: Mapping from name to :class:`Category` objects
        self.categories = {}


class Category(object):
    """Representation of a single category in a :class:`Dictionary`."""
    def __init__(self):
        #: Category name
        self.name = None
        #: Human-readable text
        self.description = None
        #: Mapping from name to :class:`Keyword` objects
        self.keywords = {}
        #: True iff this category is required in a compliant mmCIF file
        self.mandatory = None


class Keyword(object):
    """Representation of a single keyword in a :class:`Category`."""
    def __init__(self):
        #: Keyword name
        self.name = None
        #: True iff this keyword is required in a compliant mmCIF file
        self.mandatory = None


class _DictionaryReader(object):
    """Track information for a Dictionary being read from a file."""
    def __init__(self):
        self.dictionary = Dictionary()
        self._reset_category()
        self._reset_keyword()

    def _reset_category(self):
        self.category = Category()
        self.category_good = False

    def _reset_keyword(self):
        self.keyword = Keyword()
        self.keyword_good = False

    def end_save_frame(self):
        if self.keyword_good:
            k = self.keyword
            # If the owning category does not exist, make it; this can happen
            # if we extend something in the core dictionary
            # (e.g. atom_site.ihm_model_id)
            if k._category not in self.dictionary.categories:
                c = Category()
                c.name = k._category
                self.dictionary.categories[k._category] = c
            else:
                c = self.dictionary.categories[k._category]
            del k._category
            c.keywords[k.name] = k
            self._reset_keyword()
        if self.category_good:
            c = self.category
            self.dictionary.categories[c.name] = c
            self._reset_category()


class _CategoryHandler(_Handler):
    category = '_category'

    def __call__(self, id, description, mandatory_code):
        c = self.sysr.category
        c.name, c.description = id, description
        c.mandatory = _get_bool(mandatory_code)
        self.sysr.category_good = True

    def end_save_frame(self):
        self.sysr.end_save_frame()


class _ItemHandler(_Handler):
    category = '_item'

    def __call__(self, name, category_id, mandatory_code):
        cat, name = name.split('.')
        k = self.sysr.keyword
        k.name, k._category = name, category_id
        k.mandatory = _get_bool(mandatory_code)
        self.sysr.keyword_good = True


def read(fh):
    """Read dictionary data from the mmCIF file handle `fh`."""
    r = ihm.format.CifReader(fh, {})
    s = _DictionaryReader()
    handlers = [_CategoryHandler(s), _ItemHandler(s)]
    r.category_handler = dict((h.category, h) for h in handlers)
    r.read_file()
    return s.dictionary
