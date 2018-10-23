"""Classes to read in and represent an mmCIF extension dictionary"""

import ihm.reader
import ihm.format
import ihm.format_bcif
import re
import itertools

from ihm.reader import _Handler, _get_bool

class ValidatorError(Exception):
    """Exception raised if a file fails to validate.
       See :meth:`Dictionary.validate`."""
    pass


class _ValidatorCategoryHandler(_Handler):
    def __init__(self, sysr, category):
        super(_ValidatorCategoryHandler, self).__init__(sysr)
        self.category = '_' + category.name
        self.category_obj = category
        self._keys = [k for k in category.keywords.keys()]
        self.link_keys = set()
        li = sysr.dictionary.linked_items
        for link in itertools.chain(li.keys(), li.values()):
            cat, key = link.split('.')
            if cat == self.category:
                self.link_keys.add(key)

    def __call__(self, *args):
        self.sysr.validate_data(self.category_obj, self._keys, args,
                                self.link_keys)


class _ValidatorReader(object):
    """Track information used for validation while reading an mmCIF file"""
    def __init__(self, dictionary):
        self.dictionary = dictionary
        self._seen_categories = set()
        # Keep track of all values (IDs) seen for keys that are involved in
        # parent-child relationships
        self._seen_ids = {}
        li = dictionary.linked_items
        for link in itertools.chain(li.keys(), li.values()):
            self._seen_ids[link] = set()
        self.errors = []

    def validate_data(self, category, keywords, args, link_keys):
        self._seen_categories.add(category.name)
        for key, value in zip(keywords, args):
            if key in link_keys and value is not None:
                self._seen_ids["_%s.%s" % (category.name, key)].add(value)
            kwobj = category.keywords[key]
            # todo: We cannot currently detect values that are genuinely
            # missing from the file because they just show up as None in Python
            if kwobj.mandatory and value == ihm.unknown:
                self.errors.append("Mandatory keyword %s.%s cannot have "
                                   "value '?'" % (category.name, key))
            if value is None or value == ihm.unknown:
                continue
            if kwobj.enumeration and value not in kwobj.enumeration:
                self.errors.append("Keyword %s.%s value %s is not a valid "
                                   "enumerated value (options are %s)"
                                   % (category.name, key, value,
                                      ", ".join(sorted(kwobj.enumeration))))
            if kwobj.item_type and not kwobj.item_type.regex.match(value):
                self.errors.append("Keyword %s.%s value %s does not match "
                                   "item type (%s) regular expression (%s)"
                                   % (category.name, key, value,
                                      kwobj.item_type.name,
                                      kwobj.item_type.construct))

    def _check_mandatory_categories(self):
        all_categories = self.dictionary.categories
        mandatory_categories = [c.name for c in all_categories.values()
                                if c.mandatory]
        missing = set(mandatory_categories) - self._seen_categories
        if missing:
            self.errors.append("The following mandatory categories are missing "
                               "in the file: %s" % ", ".join(sorted(missing)))

    def _check_linked_items(self):
        """Check to make sure any ID referenced by a child item is defined
           in the parent"""
        for child, parent in self.dictionary.linked_items.items():
            if not self._seen_ids[child] <= self._seen_ids[parent]:
                # Strip _ prefix from category
                cat, key = parent[1:].split('.')
                # Only warn about relationships where the parent is defined
                # in this dictionary (e.g. a lot of IHM items point back
                # to PDBx categories)
                if cat in self.dictionary.categories:
                    missing = self._seen_ids[child] - self._seen_ids[parent]
                    self.errors.append("The following IDs referenced by %s "
                            "were not defined in the parent category (%s): %s"
                            % (child, parent, ", ".join(missing)))

    def report_errors(self):
        self._check_mandatory_categories()
        self._check_linked_items()
        if self.errors:
            raise ValidatorError("\n\n".join(self.errors))


class Dictionary(object):
    """Representation of an mmCIF dictionary.
       See :func:`read` to create a Dictionary from a file.

       Multiple Dictionaries can be added together to yield a Dictionary
       that includes all the data in the original Dictionaries."""
    def __init__(self):
        #: Mapping from name to :class:`Category` objects
        self.categories = {}

        #: Links between items; keys are children, values are parents e.g.
        #: ``linked_items['_ihm_starting_model_details.asym_id'] =
        #: '_struct_asym.id'``
        self.linked_items = {}

    def __iadd__(self, other):
        self.categories.update(other.categories)
        self.linked_items.update(other.linked_items)
        return self

    def __add__(self, other):
        d = Dictionary()
        d += self
        d += other
        return d

    def validate(self, fh, format='mmCIF'):
        """Validate the given file against this dictionary.

           :param file fh: The file handle to read from.
           :param str format: The format of the file. This can be 'mmCIF' (the
              default) for the (text-based) mmCIF format or 'BCIF' for
              BinaryCIF.
           :raises: :class:`ValidatorError` if the file fails to validate.

           .. note:: Only basic validation is performed. In particular, extra
              categories or keywords that are not present in the dictionary
              are ignored rather than treated as errors.
        """
        reader_map = {'mmCIF': ihm.format.CifReader,
                      'BCIF': ihm.format_bcif.BinaryCifReader}
        r = reader_map[format](fh, {})
        s = _ValidatorReader(self)
        handlers = [_ValidatorCategoryHandler(s, cat)
                    for cat in self.categories.values()]
        r.category_handler = dict((h.category, h) for h in handlers)
        # Read all data blocks
        while r.read_file():
            pass
        s.report_errors()


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


class ItemType(object):
    """Represent the type of a data item.
       This keeps the set of valid strings for values of a given
       :class:`Keyword`. For example, integer values can only contain
       the digits 0-9 with an optional +/- prefix."""
    def __init__(self, name, construct):
        self.name, self.construct = name, construct
        # Ensure that regex matches the entire value
        self.regex = re.compile(construct + '$')


class Keyword(object):
    """Representation of a single keyword in a :class:`Category`."""
    def __init__(self):
        #: Keyword name
        self.name = None
        #: True iff this keyword is required in a compliant mmCIF file
        self.mandatory = None
        #: Set of acceptable values, or None
        self.enumeration = None
        #: :class:`ItemType` for this keyword, or None
        self.item_type = None


class _DictionaryReader(object):
    """Track information for a Dictionary being read from a file."""
    def __init__(self):
        self.dictionary = Dictionary()
        self.item_types = {} # Mapping from name to ItemType object
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
        # If category_id is missing, strip leading _ from the keyword's
        # own category name and use that instead
        if category_id is None:
            category_id = cat[1:]
        k.name, k._category = name, category_id
        k.mandatory = _get_bool(mandatory_code)
        self.sysr.keyword_good = True


class _ItemEnumerationHandler(_Handler):
    category = '_item_enumeration'

    def __call__(self, value):
        k = self.sysr.keyword
        if k.enumeration is None:
            k.enumeration = set()
        k.enumeration.add(value)


class _ItemTypeListHandler(_Handler):
    category = '_item_type_list'

    def __call__(self, code, construct):
        it = ItemType(code, construct)
        self.sysr.item_types[it.name] = it


class _ItemTypeHandler(_Handler):
    category = '_item_type'

    def __call__(self, code):
        k = self.sysr.keyword
        k.item_type = code

    def finalize(self):
        for c in self.sysr.dictionary.categories.values():
            for k in c.keywords.values():
                if k.item_type is not None:
                    # Map unrecognized type codes to None
                    # For example, the ihm dictionary often uses the
                    # 'atcode' type which is not defined in the dictionary
                    # itself (but presumably is in the base PDBx dict)
                    k.item_type = self.sysr.item_types.get(k.item_type)


class _ItemLinkedHandler(_Handler):
    category = '_item_linked'

    def __call__(self, child_name, parent_name):
         self.sysr.dictionary.linked_items[child_name] = parent_name


def read(fh):
    """Read dictionary data from the mmCIF file handle `fh`.

       :return: The dictionary data.
       :rtype: :class:`Dictionary`
    """
    r = ihm.format.CifReader(fh, {})
    s = _DictionaryReader()
    handlers = [_CategoryHandler(s), _ItemHandler(s),
                _ItemEnumerationHandler(s),
                _ItemTypeListHandler(s), _ItemTypeHandler(s),
                _ItemLinkedHandler(s)]
    r.category_handler = dict((h.category, h) for h in handlers)
    r.read_file()
    for h in handlers:
        h.finalize()
    return s.dictionary
