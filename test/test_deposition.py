import utils
import os
import unittest
import sys
import warnings
from io import StringIO, BytesIO
from test_format_bcif import MockMsgPack, MockFh, _add_msgpack

TOPDIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
utils.set_search_paths(TOPDIR)
import ihm.deposition
import ihm.dictionary
import ihm.format_bcif

try:
    from ihm import _format
except ImportError:
    _format = None


RULE_HEADER = """
loop_
_pdbx_deposition_rule.id
_pdbx_deposition_rule.family
_pdbx_deposition_rule.severity
_pdbx_deposition_rule.scope_category
_pdbx_deposition_rule.procedural_method
_pdbx_deposition_rule.message
_pdbx_deposition_rule.enabled
_pdbx_deposition_rule.param_flag
_pdbx_deposition_rule.join_flag
_pdbx_deposition_rule.row_selection_flag
"""

CONDITION_HEADER = """
loop_
_pdbx_deposition_rule_condition.rule_id
_pdbx_deposition_rule_condition.ordinal
_pdbx_deposition_rule_condition.role
_pdbx_deposition_rule_condition.item_name
_pdbx_deposition_rule_condition.operator
_pdbx_deposition_rule_condition.value
_pdbx_deposition_rule_condition.compare_item_name
_pdbx_deposition_rule_condition.group_operator
_pdbx_deposition_rule_condition.quantifier
_pdbx_deposition_rule_condition.value_transform
"""


def make_rules(rules, conditions, extra=""):
    """Make a Rules object from rule and condition loop rows"""
    cif = RULE_HEADER + rules + CONDITION_HEADER + conditions + extra
    return ihm.deposition.read(StringIO(cif))


def make_rule(scope, conditions, severity='ERROR', family='conditional_value',
              flags='NO NO NO', extra=""):
    """Make a Rules object containing a single rule R1"""
    rules = ("R1 %s %s %s . 'test message' YES %s\n"
             % (family, severity, scope, flags))
    return make_rules(rules, conditions, extra)


def run_validate(rules, cif, dictionary=None):
    """Validate the given CIF text; return a list of (rule id, row) for
       all violations, sorted"""
    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter("always")
        try:
            violations = rules.validate(StringIO(cif), dictionary=dictionary)
        except ihm.deposition.RuleError as err:
            violations = err.violations
        violations = list(violations)
        for x in w:
            if isinstance(x.message, ihm.deposition.RuleWarning):
                violations.append(x.message.violation)
    return sorted(set((v.rule.id, v.row) for v in violations))


def make_dictionary():
    """Make a simple test dictionary"""
    d = ihm.dictionary.Dictionary()
    code = ihm.dictionary.ItemType('code', 'char', r'[A-Za-z0-9_-]+')
    ucode = ihm.dictionary.ItemType('ucode', 'uchar', r'[A-Za-z0-9_-]+')
    intt = ihm.dictionary.ItemType('int', 'numb', r'[+-]?[0-9]+')
    d.item_types = {'code': code, 'ucode': ucode, 'int': intt}
    c = ihm.dictionary.Category()
    c.name = 'foo'
    for name, typ in (('cs', code), ('ci', ucode), ('num', intt),
                      ('kind', ucode), ('other', code)):
        k = ihm.dictionary.Keyword()
        k.name, k.item_type = name, typ
        c.keywords[name] = k
    enum = ihm.dictionary._KeywordEnumeration()
    enum.case_sensitive = False
    enum.add('fruit')
    enum.details['fruit'] = 'APPLE, PEAR'
    enum.add('nodetail')
    c.keywords['kind'].enumeration = enum
    d.categories[c.name] = c
    return d


class Tests(unittest.TestCase):
    def test_read(self):
        """Test read() function"""
        cif = RULE_HEADER + """
R1 conditional_presence ERROR entry . 'msg 1' YES YES YES YES
R2 procedural warning atom_site seq_check 'msg 2' NO NO NO NO
""" + CONDITION_HEADER + """
R1 2 THEN '_foo.x' NOT_EMPTY . . . ANY .
R1 1 when '_bar.y' EQ 1 '_bar.z' OR . ABS
#
loop_
_pdbx_deposition_rule_param.rule_id
_pdbx_deposition_rule_param.name
_pdbx_deposition_rule_param.value
R1 group_by '_foo.x,_foo.y'
#
loop_
_pdbx_deposition_rule_join.rule_id
_pdbx_deposition_rule_join.ordinal
_pdbx_deposition_rule_join.scope_item_names
_pdbx_deposition_rule_join.partner_item_names
_pdbx_deposition_rule_join.on_no_match
R1 2 '_entry.id' '_foo.x' .
R1 1 '_entry.id' '_bar.y' FAIL
#
loop_
_pdbx_deposition_rule_row_selection.rule_id
_pdbx_deposition_rule_row_selection.category_id
_pdbx_deposition_rule_row_selection.selector
_pdbx_deposition_rule_row_selection.selector_item
_pdbx_deposition_rule_row_selection.group_by
_pdbx_deposition_rule_row_selection.exclude_items
R1 foo MIN '_foo.x' '_foo.y' .
"""
        rules = ihm.deposition.read(StringIO(cif))
        self.assertEqual(sorted(rules.rules.keys()), ['R1', 'R2'])
        r1 = rules.rules['R1']
        self.assertEqual(r1.family, 'conditional_presence')
        self.assertEqual(r1.severity, 'ERROR')
        self.assertEqual(r1.scope_category, 'entry')
        self.assertIsNone(r1.procedural_method)
        self.assertEqual(r1.message, 'msg 1')
        self.assertTrue(r1.enabled)
        self.assertTrue(r1.param_flag)
        self.assertTrue(r1.join_flag)
        self.assertTrue(r1.row_selection_flag)
        self.assertEqual([c.ordinal for c in r1.conditions], [1, 2])
        c = r1.conditions[0]
        self.assertEqual(c.role, 'WHEN')
        self.assertEqual(c.item_name, '_bar.y')
        self.assertEqual(c.operator, 'EQ')
        self.assertEqual(c.value, '1')
        self.assertEqual(c.compare_item_name, '_bar.z')
        self.assertEqual(c.group_operator, 'OR')
        self.assertIsNone(c.quantifier)
        self.assertEqual(c._get_quantifier(), 'ANY')
        self.assertEqual(c.value_transform, 'ABS')
        self.assertEqual(r1.conditions[1]._get_quantifier(), 'ANY')
        self.assertEqual(r1.params, {'group_by': '_foo.x,_foo.y'})
        self.assertEqual([j.ordinal for j in r1.joins], [1, 2])
        self.assertEqual(r1.joins[0].on_no_match, 'FAIL')
        self.assertEqual(r1.joins[1].on_no_match, 'SKIP')
        self.assertEqual(len(r1.row_selections), 1)
        rs = r1.row_selections[0]
        self.assertEqual(rs.category_id, 'foo')
        self.assertEqual(rs.selector, 'MIN')
        self.assertEqual(rs.selector_item, '_foo.x')
        self.assertEqual(rs.group_by, '_foo.y')
        self.assertIsNone(rs.exclude_items)
        r2 = rules.rules['R2']
        self.assertEqual(r2.severity, 'WARNING')
        self.assertEqual(r2.procedural_method, 'seq_check')
        self.assertFalse(r2.enabled)
        self.assertFalse(r2.param_flag)

    def test_read_defaults(self):
        """Test read() with default flag values"""
        cif = """
_pdbx_deposition_rule.id R1
_pdbx_deposition_rule.family format
_pdbx_deposition_rule.severity ERROR
_pdbx_deposition_rule.scope_category entry
_pdbx_deposition_rule.message msg
"""
        rules = ihm.deposition.read(StringIO(cif))
        r1 = rules.rules['R1']
        self.assertTrue(r1.enabled)
        self.assertFalse(r1.param_flag)
        self.assertFalse(r1.join_flag)
        self.assertFalse(r1.row_selection_flag)

    def test_read_ordinals_and_flags(self):
        """Test read() with non-integer ordinals and unknown flags"""
        rules = make_rules(
            "R1 format ERROR foo . msg ? ? ? ?\n", """
R1 b THEN '_foo.x' NOT_EMPTY . . . . .
R1 a THEN '_foo.y' NOT_EMPTY . . . . .
R1 2 THEN '_foo.z' NOT_EMPTY . . . . .
R1 ? THEN '_foo.w' NOT_EMPTY . . . . .
""")
        r1 = rules.rules['R1']
        # Integer ordinals sort before non-integer ones
        self.assertEqual([c.ordinal for c in r1.conditions],
                         [2, None, 'a', 'b'])
        # Unknown flags take their default values
        self.assertTrue(r1.enabled)
        self.assertFalse(r1.param_flag)
        self.assertFalse(r1.join_flag)
        self.assertFalse(r1.row_selection_flag)

    def test_read_multiple_blocks(self):
        """Test read() of rules spread over multiple data blocks"""
        cif = ("data_a\n" + RULE_HEADER
               + "R1 format ERROR foo . msg YES NO NO NO\n"
               + "data_b\n" + RULE_HEADER
               + "R2 format ERROR foo . msg YES NO NO NO\n"
               + CONDITION_HEADER
               + "R1 1 THEN '_foo.x' NOT_EMPTY . . . . .\n")
        rules = ihm.deposition.read(StringIO(cif))
        self.assertEqual(sorted(rules.rules.keys()), ['R1', 'R2'])
        self.assertEqual(len(rules.rules['R1'].conditions), 1)

    def test_read_bad_rule_id(self):
        """Test read() with a condition referring to an undefined rule"""
        self.assertRaises(ValueError, make_rules,
                          "R2 format ERROR foo . msg YES NO NO NO\n",
                          "R1 1 THEN '_foo.x' NOT_EMPTY . . . . .\n")

    def test_read_binary_cif(self):
        """Test read() function with BinaryCIF input"""
        sys.modules['msgpack'] = MockMsgPack
        fh = MockFh()
        writer = ihm.format_bcif.BinaryCifWriter(fh)
        writer.start_block('rules')
        with writer.category('_pdbx_deposition_rule') as loc:
            loc.write(id='R1', family='format', severity='WARNING',
                      scope_category='foo', message='msg', enabled='YES')
        with writer.loop('_pdbx_deposition_rule_condition',
                         ['rule_id', 'ordinal', 'role', 'item_name',
                          'operator']) as lp:
            lp.write(rule_id='R1', ordinal=1, role='THEN',
                     item_name='_foo.x', operator='NOT_EMPTY')
        writer.flush()
        if _format:
            bio = BytesIO()
            _add_msgpack(fh.data, bio)
            bio.seek(0)
            fh.data = bio
        rules = ihm.deposition.read(fh.data, format='BCIF')
        r1 = rules.rules['R1']
        self.assertEqual(r1.severity, 'WARNING')
        self.assertEqual(len(r1.conditions), 1)
        self.assertEqual(r1.conditions[0].operator, 'NOT_EMPTY')

    def test_add(self):
        """Test adding Rules objects"""
        r1 = make_rule('foo', "R1 1 THEN '_foo.x' NOT_EMPTY . . . . .\n")
        r2 = make_rules("R2 format ERROR foo . msg YES NO NO NO\n",
                        "R2 1 THEN '_foo.x' NOT_EMPTY . . . . .\n")
        r = r1 + r2
        self.assertEqual(sorted(r.rules.keys()), ['R1', 'R2'])
        self.assertEqual(sorted(r1.rules.keys()), ['R1'])

    def test_validate_error(self):
        """Test validate() reporting of errors"""
        rules = make_rule('foo', "R1 1 THEN '_foo.x' NOT_EMPTY . . . . .\n")
        self.assertEqual(rules.validate(StringIO("_foo.x 1")), [])
        with self.assertRaises(ihm.deposition.RuleError) as cm:
            rules.validate(StringIO("_foo.x ?"))
        self.assertEqual(str(cm.exception),
                         "ERROR R1: test message [foo row 1]")
        self.assertEqual(len(cm.exception.violations), 1)

    def test_validate_warning_info(self):
        """Test validate() reporting of warnings and info"""
        for severity, cls in (('WARNING', ihm.deposition.RuleWarning),
                              ('INFO', ihm.deposition.RuleInfo)):
            rules = make_rule('foo', "R1 1 THEN '_foo.x' NOT_EMPTY "
                              ". . . . .\n", severity=severity)
            with warnings.catch_warnings(record=True) as w:
                warnings.simplefilter("always")
                v = rules.validate(StringIO("_foo.x ."))
            self.assertEqual(len(v), 1)
            self.assertEqual(len(w), 1)
            self.assertIs(w[0].category, cls)
            self.assertIs(w[0].message.violation, v[0])
            self.assertEqual(str(w[0].message),
                             "%s R1: test message [foo row 1]" % severity)

    def test_validate_disabled(self):
        """Test that disabled rules are not checked"""
        rules = make_rules("R1 format ERROR foo . msg NO NO NO NO\n",
                           "R1 1 THEN '_foo.x' NOT_EMPTY . . . . .\n")
        self.assertEqual(run_validate(rules, "_foo.x ?"), [])

    def test_validate_unsupported(self):
        """Test that unsupported rules are skipped with a warning"""
        rules = make_rules("""
R1 procedural ERROR foo check msg YES NO NO NO
R2 format ERROR foo . msg YES NO NO NO
R3 aggregate ERROR foo . msg YES YES NO NO
""", "R3 1 THEN '_foo.x' LE 1 . . . .", """
loop_
_pdbx_deposition_rule_param.rule_id
_pdbx_deposition_rule_param.name
_pdbx_deposition_rule_param.value
R3 aggregate MEDIAN
""")
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            rules.validate(StringIO("_foo.x ?"))
        self.assertEqual(len(w), 3)
        for x in w:
            self.assertIs(x.category, ihm.deposition.UnsupportedRuleWarning)

    def test_validate_absent_scope(self):
        """Test validation when the scope category is absent"""
        rules = make_rule('entry', "R1 1 THEN '_entry.id' NOT_EMPTY "
                          ". . . . .\n")
        self.assertEqual(run_validate(rules, "_entry.id x"), [])
        self.assertEqual(run_validate(rules, "_foo.x y"),
                         [('R1', 'entry category is absent')])
        # Comparison rules should not fire if the category is absent
        rules = make_rule('foo', """
R1 1 WHEN '_foo.x' EQ y . . . .
R1 2 THEN '_bar.x' NOT_EMPTY . . . ANY .
""")
        self.assertEqual(run_validate(rules, "_entry.id x"), [])
        self.assertEqual(run_validate(rules, "_foo.x y"),
                         [('R1', 'foo row 1')])

    def test_validate_multiple_rows(self):
        """Test validation of each row in the scope category"""
        rules = make_rule('foo', """
R1 1 WHEN '_foo.x' IN 'a, b,c' . . . .
R1 2 THEN '_bar.x' NOT_EMPTY . . . ANY .
""")
        cif = """
loop_
_foo.x
a
b
c
d
?
"""
        self.assertEqual(run_validate(rules, cif),
                         [('R1', 'foo row 1'), ('R1', 'foo row 2'),
                          ('R1', 'foo row 3')])
        self.assertEqual(run_validate(rules, cif + "_bar.x 1"), [])

    def test_validate_multiple_blocks(self):
        """Test validation of multiple data blocks"""
        rules = make_rule('foo', "R1 1 THEN '_foo.x' NOT_EMPTY . . . . .\n")
        with self.assertRaises(ihm.deposition.RuleError) as cm:
            rules.validate(StringIO("data_a\n_foo.x 1\ndata_b\n_foo.x ."))
        self.assertEqual(len(cm.exception.violations), 1)
        v = cm.exception.violations[0]
        self.assertEqual(v.data_block, 2)
        self.assertEqual(str(v), "ERROR R1: test message "
                                 "[data block 2, foo row 1]")

    def test_validate_unary(self):
        """Test validation of unary operators"""
        cif = "loop_\n_foo.id\n_foo.x\n1 a\n2 .\n3 ' '\n"
        for op, exp in (('EXISTS', []),
                        ('NOT_EXISTS', [1, 2, 3]),
                        ('EMPTY', [1]),
                        ('NOT_EMPTY', [2, 3])):
            rules = make_rule('foo', "R1 1 THEN '_foo.x' %s . . . . .\n" % op)
            self.assertEqual(run_validate(rules, cif),
                             [('R1', 'foo row %d' % i) for i in exp])
        rules = make_rule('foo', "R1 1 THEN '_foo.y' EXISTS . . . . .\n")
        self.assertEqual(len(run_validate(rules, cif)), 3)

    def test_validate_partner_quantifier(self):
        """Test ANY and ALL quantifiers over partner rows"""
        cif = "_foo.id 1\nloop_\n_bar.x\na\nb\n.\n"
        for quant, op, val, exp in (('ANY', 'NOT_EMPTY', '.', False),
                                    ('ALL', 'NOT_EMPTY', '.', True),
                                    ('ANY', 'EQ', 'a', False),
                                    ('ALL', 'EQ', 'a', True),
                                    ('ALL', 'IN', 'a,b', False),
                                    ('ANY', 'NE', 'a', False),
                                    ('ALL', 'EQ', 'z', True)):
            rules = make_rule('foo', "R1 1 THEN '_bar.x' %s %s . . %s .\n"
                              % (op, val, quant))
            self.assertEqual(bool(run_validate(rules, cif)), exp,
                             (quant, op, val))
        # No partner rows: ANY fails, ALL holds
        for quant, exp in (('ANY', True), ('ALL', False)):
            rules = make_rule('foo', "R1 1 THEN '_bar.x' NOT_EMPTY . . . "
                              "%s .\n" % quant)
            self.assertEqual(bool(run_validate(rules, "_foo.id 1")), exp)
        # Comparison with no non-missing partner values is skipped
        rules = make_rule('foo', "R1 1 THEN '_bar.x' EQ a . . ANY .\n")
        self.assertEqual(run_validate(rules, "_foo.id 1\n_bar.x ?"), [])

    def test_validate_missing_skip(self):
        """Test that comparisons with missing values are skipped"""
        cif = "_foo.x ?\n_foo.y 1"
        # THEN is treated as satisfied
        rules = make_rule('foo', "R1 1 THEN '_foo.x' EQ a . . . .\n")
        self.assertEqual(run_validate(rules, cif), [])
        # WHEN is treated as not holding
        rules = make_rule('foo', """
R1 1 WHEN '_foo.x' NE a . . . .
R1 2 THEN '_foo.y' EQ 2 . . . .
""")
        self.assertEqual(run_validate(rules, cif), [])
        # UNLESS is treated as not holding
        rules = make_rule('foo', """
R1 1 UNLESS '_foo.x' NE a . . . .
R1 2 THEN '_foo.y' EQ 2 . . . .
""")
        self.assertEqual(run_validate(rules, cif), [('R1', 'foo row 1')])

    def test_validate_group_operator(self):
        """Test AND/OR group operators"""
        for group, cif, exp in (('AND', "_foo.x 1\n_foo.y 1", False),
                                ('AND', "_foo.x 1\n_foo.y 2", True),
                                ('OR', "_foo.x 1\n_foo.y 2", False),
                                ('OR', "_foo.x 2\n_foo.y 2", True)):
            rules = make_rule('foo', """
R1 1 THEN '_foo.x' EQ 1 . %s . .
R1 2 THEN '_foo.y' EQ 1 . %s . .
""" % (group, group))
            self.assertEqual(bool(run_validate(rules, cif)), exp)

    def test_validate_numeric_compare(self):
        """Test numeric and string comparisons"""
        for op, val, cif, exp in (('LT', '10', '9', False),
                                  ('LT', '10', '10', True),
                                  ('LE', '10', '10', False),
                                  ('GT', '10', '9.5', True),
                                  ('GE', '10', '1.0e1', False),
                                  ('EQ', '1', '1.0', False),
                                  ('EQ', 'abc', 'ABC', False),
                                  ('GT', '2020-01-01', '2021-01-01', False),
                                  ('GT', '2020-01-01', '2019-12-31', True),
                                  ('LE', '1.0', '1.5(2)', True)):
            rules = make_rule('foo', "R1 1 THEN '_foo.x' %s %s . . . .\n"
                              % (op, val))
            self.assertEqual(bool(run_validate(rules, "_foo.x " + cif)),
                             exp, (op, val, cif))

    def test_validate_abs(self):
        """Test the ABS value transform"""
        rules = make_rule('foo', "R1 1 THEN '_foo.x' LE 1 . . . ABS\n")
        self.assertEqual(run_validate(rules, "_foo.x -0.5"), [])
        self.assertEqual(len(run_validate(rules, "_foo.x -1.5")), 1)
        # Non-numeric values are treated as missing
        self.assertEqual(run_validate(rules, "_foo.x abc"), [])

    def test_validate_matches(self):
        """Test MATCHES and NOT_MATCHES operators"""
        rules = make_rule('foo', "R1 1 THEN '_foo.x' MATCHES "
                          "'^[0-9][A-Za-z0-9]{3}$' . . . .\n")
        self.assertEqual(run_validate(rules, "_foo.x 1abc"), [])
        self.assertEqual(len(run_validate(rules, "_foo.x abcd")), 1)
        rules = make_rule('foo', "R1 1 THEN '_foo.x' NOT_MATCHES "
                          "'^[0-9]' . . . .\n")
        self.assertEqual(len(run_validate(rules, "_foo.x 1abc")), 1)
        self.assertEqual(run_validate(rules, "_foo.x abcd"), [])

    def test_validate_item_compare(self):
        """Test comparison of two items"""
        # Both items in the scope category
        rules = make_rule('foo', "R1 1 THEN '_foo.x' LE_ITEM . "
                          "'_foo.y' . . .\n")
        self.assertEqual(run_validate(rules, "_foo.x 1\n_foo.y 2"), [])
        self.assertEqual(len(run_validate(rules, "_foo.x 3\n_foo.y 2")), 1)
        self.assertEqual(run_validate(rules, "_foo.x 3\n_foo.y ?"), [])
        # Scope item compared with partner rows (default quantifier ALL)
        rules = make_rule('foo', "R1 1 THEN '_foo.x' GE_ITEM . "
                          "'_bar.y' . . .\n")
        cif = "_foo.x 5\nloop_\n_bar.y\n1\n4\n?\n"
        self.assertEqual(run_validate(rules, cif), [])
        self.assertEqual(len(run_validate(rules, cif + "6\n")), 1)
        # Both items in the same partner category
        rules = make_rule('foo', "R1 1 THEN '_bar.x' EQ_ITEM . "
                          "'_bar.y' . . .\n")
        cif = "_foo.x 5\nloop_\n_bar.x\n_bar.y\n1 1\n2 2\n"
        self.assertEqual(run_validate(rules, cif), [])
        self.assertEqual(len(run_validate(rules, cif + "3 4\n")), 1)
        # Other comparison operators
        for op, exp in (('LT_ITEM', True), ('GT_ITEM', False)):
            rules = make_rule('foo', "R1 1 THEN '_foo.x' %s . "
                              "'_foo.y' . . .\n" % op)
            self.assertEqual(bool(run_validate(rules,
                                               "_foo.x 3\n_foo.y 2")), exp)

    def test_validate_unique(self):
        """Test UNIQUE operator"""
        rules = make_rule('foo', "R1 1 THEN '_foo.x' UNIQUE . . . . .\n")
        cif = "loop_\n_foo.x\na\nb\na\n?\n?\n"
        self.assertEqual(run_validate(rules, cif),
                         [('R1', 'foo row 1'), ('R1', 'foo row 3')])

    def test_validate_in_column_of(self):
        """Test IN_COLUMN_OF operator"""
        rules = make_rule('foo', "R1 1 THEN '_foo.x' IN_COLUMN_OF . "
                          "'_bar.id' . . .\n")
        cif = "loop_\n_foo.x\na\nb\nc\nloop_\n_bar.id\na\nB\n?\n"
        self.assertEqual(run_validate(rules, cif), [('R1', 'foo row 3')])
        # Skipped if the column is empty
        self.assertEqual(run_validate(rules, "_foo.x a"), [])

    def test_validate_dictionary_types(self):
        """Test validation using item types from a dictionary"""
        d = make_dictionary()
        # Case sensitivity is determined by the item type
        rules = make_rule('foo', "R1 1 THEN '_foo.cs' EQ abc . . . .\n")
        self.assertEqual(run_validate(rules, "_foo.cs ABC"), [])
        self.assertEqual(len(run_validate(rules, "_foo.cs ABC", d)), 1)
        rules = make_rule('foo', "R1 1 THEN '_foo.ci' EQ abc . . . .\n")
        self.assertEqual(run_validate(rules, "_foo.ci ABC", d), [])
        # Codes are compared as strings, not numbers
        rules = make_rule('foo', "R1 1 THEN '_foo.cs' EQ 1 . . . .\n")
        self.assertEqual(run_validate(rules, "_foo.cs 01"), [])
        self.assertEqual(len(run_validate(rules, "_foo.cs 01", d)), 1)
        # Values that don't match their type are treated as missing
        rules = make_rule('foo', "R1 1 THEN '_foo.num' NOT_EMPTY . . . . .\n")
        self.assertEqual(run_validate(rules, "_foo.num 1.5"), [])
        self.assertEqual(len(run_validate(rules, "_foo.num 1.5", d)), 1)

    def test_validate_matches_type(self):
        """Test MATCHES_TYPE operator"""
        d = make_dictionary()
        rules = make_rule('foo', "R1 1 THEN '_foo.other' MATCHES_TYPE "
                          "'int, bad' . . . .\n")
        self.assertEqual(run_validate(rules, "_foo.other 42", d), [])
        self.assertEqual(len(run_validate(rules, "_foo.other abc", d)), 1)
        # Skipped without a dictionary, or if no types are known
        self.assertEqual(run_validate(rules, "_foo.other abc"), [])
        rules = make_rule('foo', "R1 1 THEN '_foo.other' MATCHES_TYPE "
                          "bad . . . .\n")
        self.assertEqual(run_validate(rules, "_foo.other abc", d), [])

    def test_validate_in_enumeration_details(self):
        """Test IN_ENUMERATION_DETAILS_OF operator"""
        d = make_dictionary()
        rules = make_rule('foo', "R1 1 THEN '_foo.ci' "
                          "IN_ENUMERATION_DETAILS_OF . '_foo.kind' . . .\n")
        self.assertEqual(run_validate(rules, "_foo.ci pear\n_foo.kind FRUIT",
                                      d), [])
        self.assertEqual(len(run_validate(
            rules, "_foo.ci carrot\n_foo.kind fruit", d)), 1)
        # Skipped if no detail, value not enumerated, or no dictionary
        for kind in ('nodetail', 'other'):
            self.assertEqual(run_validate(
                rules, "_foo.ci carrot\n_foo.kind %s" % kind, d), [])
        self.assertEqual(run_validate(
            rules, "_foo.ci carrot\n_foo.kind fruit"), [])

    def test_validate_join(self):
        """Test joins between scope and partner categories"""
        joins = """
loop_
_pdbx_deposition_rule_join.rule_id
_pdbx_deposition_rule_join.ordinal
_pdbx_deposition_rule_join.scope_item_names
_pdbx_deposition_rule_join.partner_item_names
_pdbx_deposition_rule_join.on_no_match
R1 1 '_foo.id' '_bar.foo_id' %s
"""
        conds = "R1 1 THEN '_bar.x' NOT_EMPTY . . . ANY .\n"
        cif = """
loop_
_foo.id
1
2
3
?
loop_
_bar.foo_id
_bar.x
1 a
2 .
"""
        rules = make_rule('foo', conds, flags='NO YES NO',
                          extra=joins % 'SKIP')
        self.assertEqual(run_validate(rules, cif), [('R1', 'foo row 2')])
        rules = make_rule('foo', conds, flags='NO YES NO',
                          extra=joins % 'FAIL')
        self.assertEqual(run_validate(rules, cif),
                         [('R1', 'foo row 2'), ('R1', 'foo row 3'),
                          ('R1', 'foo row 4')])
        # Joins are ignored if join_flag is NO
        rules = make_rule('foo', conds, flags='NO NO NO',
                          extra=joins % 'FAIL')
        self.assertEqual(run_validate(rules, cif), [])

    def test_validate_join_single_row_fallback(self):
        """Test joins with SINGLE_ROW_FALLBACK"""
        joins = """
loop_
_pdbx_deposition_rule_join.rule_id
_pdbx_deposition_rule_join.ordinal
_pdbx_deposition_rule_join.scope_item_names
_pdbx_deposition_rule_join.partner_item_names
_pdbx_deposition_rule_join.on_no_match
R1 1 '_foo.id' '_bar.foo_id' SINGLE_ROW_FALLBACK
"""
        rules = make_rule('foo', "R1 1 THEN '_foo.x' LE_ITEM . '_bar.x' "
                          ". . .\n", flags='NO YES NO', extra=joins)
        # Join items absent, one row each: pair them
        self.assertEqual(len(run_validate(rules, "_foo.x 2\n_bar.x 1")), 1)
        # Join items absent, multiple rows: skip
        self.assertEqual(run_validate(
            rules, "_foo.x 2\nloop_\n_bar.x\n1\n0\n"), [])
        # Join items present but no match: skip
        self.assertEqual(run_validate(
            rules, "_foo.x 2\n_foo.id 1\n_bar.x 1\n_bar.foo_id 2"), [])

    def test_validate_row_selection(self):
        """Test MIN/MAX row selection"""
        sel = """
loop_
_pdbx_deposition_rule_row_selection.rule_id
_pdbx_deposition_rule_row_selection.category_id
_pdbx_deposition_rule_row_selection.selector
_pdbx_deposition_rule_row_selection.selector_item
_pdbx_deposition_rule_row_selection.group_by
R1 foo %s '_foo.res' %s
"""
        conds = "R1 1 THEN '_foo.x' EQ ok . . . .\n"
        cif = """
loop_
_foo.grp
_foo.res
_foo.x
A 1.0 bad
A 2.0 bad
A 3.0 bad
B 0.5 bad
B 0.5 bad
B ? bad
"""
        rules = make_rule('foo', conds, flags='NO NO YES',
                          extra=sel % ('MIN', '.'))
        self.assertEqual(run_validate(rules, cif),
                         [('R1', 'foo row 4'), ('R1', 'foo row 5')])
        rules = make_rule('foo', conds, flags='NO NO YES',
                          extra=sel % ('MAX', "'_foo.grp'"))
        self.assertEqual(run_validate(rules, cif),
                         [('R1', 'foo row 3'), ('R1', 'foo row 4'),
                          ('R1', 'foo row 5')])
        # Row selection is ignored if row_selection_flag is NO
        rules = make_rule('foo', conds, flags='NO NO NO',
                          extra=sel % ('MIN', '.'))
        self.assertEqual(len(run_validate(rules, cif)), 6)

    def test_validate_row_selection_partner(self):
        """Test row selection on a partner category"""
        sel = """
_pdbx_deposition_rule_row_selection.rule_id R1
_pdbx_deposition_rule_row_selection.category_id bar
_pdbx_deposition_rule_row_selection.selector MAX
_pdbx_deposition_rule_row_selection.selector_item '_bar.res'
"""
        rules = make_rule('foo', "R1 1 THEN '_foo.x' GE_ITEM . '_bar.x' "
                          ". . .\n", flags='NO NO YES', extra=sel)
        cif = "_foo.x 5\nloop_\n_bar.res\n_bar.x\n1 10\n2 4\n"
        self.assertEqual(run_validate(rules, cif), [])

    def test_validate_row_selection_any_value(self):
        """Test ANY_VALUE row selection"""
        sel = """
_pdbx_deposition_rule_row_selection.rule_id R1
_pdbx_deposition_rule_row_selection.category_id foo
_pdbx_deposition_rule_row_selection.selector ANY_VALUE
_pdbx_deposition_rule_row_selection.exclude_items '_foo.cs'
"""
        rules = make_rule('foo', "R1 1 THEN '_foo.ci' NOT_EMPTY "
                          ". . . . .\n", flags='NO NO YES', extra=sel)
        cif = """
loop_
_foo.cs
_foo.ci
_foo.num
_foo.other
1 ? 1 .
2 ? . .
3 ? . x
"""
        # With a dictionary, all items in the category are considered
        self.assertEqual(run_validate(rules, cif, make_dictionary()),
                         [('R1', 'foo row 1'), ('R1', 'foo row 3')])
        # Without, only items referenced by the rule are
        self.assertEqual(run_validate(rules, cif), [])

    def test_validate_aggregate(self):
        """Test aggregate rules"""
        params = """
loop_
_pdbx_deposition_rule_param.rule_id
_pdbx_deposition_rule_param.name
_pdbx_deposition_rule_param.value
R1 group_by '_foo.a,_foo.b'
R1 aggregate SUM
"""
        rules = make_rule('foo', """
R1 1 WHEN '_foo.ok' NE no . . . .
R1 2 THEN '_foo.occ' LE 1.0 . . . .
""", family='aggregate', flags='YES NO NO', extra=params)
        cif = """
loop_
_foo.a
_foo.b
_foo.occ
_foo.ok
A 1 0.5 yes
A 1 0.5 yes
A 2 0.6 yes
A 2 0.6 no
A 3 0.6 yes
A 3 0.6 yes
A 3 ? yes
B 1 ? yes
"""
        self.assertEqual(run_validate(rules, cif),
                         [('R1', 'group of 3 foo rows (foo.a=A, foo.b=3)')])

    def test_validate_aggregate_join(self):
        """Test aggregate rules with joins and partner conditions"""
        params = """
loop_
_pdbx_deposition_rule_param.rule_id
_pdbx_deposition_rule_param.name
_pdbx_deposition_rule_param.value
R1 aggregate SUM
#
loop_
_pdbx_deposition_rule_join.rule_id
_pdbx_deposition_rule_join.ordinal
_pdbx_deposition_rule_join.scope_item_names
_pdbx_deposition_rule_join.partner_item_names
_pdbx_deposition_rule_join.on_no_match
R1 1 '_foo.id' '_bar.foo_id' FAIL
"""
        rules = make_rule('foo', """
R1 1 THEN '_foo.occ' LE 1.0 . . . .
R1 2 THEN '_bar.x' NOT_EMPTY . . . ANY .
""", family='aggregate', flags='YES YES NO', extra=params)
        cif = """
loop_
_foo.id
_foo.occ
1 0.4
2 0.4
3 0.4
loop_
_bar.foo_id
_bar.x
1 a
2 b
"""
        # Row 3 has no partner, so is excluded from the sum
        self.assertEqual(run_validate(rules, cif), [])
        # Partner conditions are checked using the first row's partners
        self.assertEqual(run_validate(rules, cif.replace("1 a", "1 .")),
                         [('R1', 'group of 2 foo rows ()')])
        # Sum includes all rows that have partners
        self.assertEqual(run_validate(rules, cif + "3 c\n"),
                         [('R1', 'group of 3 foo rows ()')])

    def test_validate_join_fail_detail(self):
        """Test reporting of failed joins"""
        joins = """
_pdbx_deposition_rule_join.rule_id R1
_pdbx_deposition_rule_join.ordinal 1
_pdbx_deposition_rule_join.scope_item_names '_foo.id'
_pdbx_deposition_rule_join.partner_item_names '_bar.foo_id'
_pdbx_deposition_rule_join.on_no_match FAIL
"""
        rules = make_rule('foo', "R1 1 THEN '_bar.x' NOT_EMPTY . . . . .\n",
                          flags='NO YES NO', extra=joins)
        with self.assertRaises(ihm.deposition.RuleError) as cm:
            rules.validate(StringIO("_foo.id 1\n_bar.foo_id 2\n_bar.x a"))
        v, = cm.exception.violations
        self.assertEqual(v.detail, "no matching row in bar")
        self.assertEqual(str(v), "ERROR R1: test message [foo row 1] "
                                 "(no matching row in bar)")

    def test_validate_missing_condition_value(self):
        """Test that operators lacking a value are skipped"""
        for op in ('EQ', 'IN', 'NOT_IN', 'MATCHES', 'NOT_MATCHES'):
            rules = make_rule('foo', "R1 1 THEN '_foo.x' %s . . . . .\n" % op)
            self.assertEqual(run_validate(rules, "_foo.x a"), [], op)

    def test_validate_regex_cache(self):
        """Test that a regex is applied correctly to multiple rows"""
        rules = make_rule('foo', "R1 1 THEN '_foo.x' MATCHES '^a' "
                          ". . . .\n")
        cif = "loop_\n_foo.x\nab\nba\nac\n"
        self.assertEqual(run_validate(rules, cif), [('R1', 'foo row 2')])

    def test_validate_item_name_no_underscore(self):
        """Test item names given without a leading underscore"""
        rules = make_rule('FOO', "R1 1 THEN 'Foo.X' EQ a . . . .\n")
        self.assertEqual(run_validate(rules, "_foo.x a"), [])
        self.assertEqual(run_validate(rules, "_foo.x b"),
                         [('R1', 'foo row 1')])

    def test_validate_category_not_in_dictionary(self):
        """Test items whose category is not in the dictionary"""
        d = make_dictionary()
        rules = make_rule('bar', "R1 1 THEN '_bar.x' EQ abc . . . .\n")
        # No type information, so compared case-insensitively
        self.assertEqual(run_validate(rules, "_bar.x ABC", d), [])
        self.assertEqual(run_validate(rules, "_bar.x xyz", d),
                         [('R1', 'bar row 1')])

    def test_validate_bad_rules(self):
        """Test validation with malformed rules"""
        # Unknown condition role
        rules = make_rule('foo', "R1 1 MAYBE '_foo.x' EQ a . . . .\n"
                          "R1 2 THEN '_foo.x' EQ a . . . .\n")
        self.assertRaises(ValueError, rules.validate, StringIO("_foo.x a"))
        # Unknown operator
        rules = make_rule('foo', "R1 1 THEN '_foo.x' FROB a . . . .\n")
        self.assertRaises(ValueError, rules.validate, StringIO("_foo.x a"))
        # Unknown row selector
        sel = """
_pdbx_deposition_rule_row_selection.rule_id R1
_pdbx_deposition_rule_row_selection.category_id foo
_pdbx_deposition_rule_row_selection.selector MEDIAN
_pdbx_deposition_rule_row_selection.selector_item '_foo.x'
"""
        rules = make_rule('foo', "R1 1 THEN '_foo.x' EQ a . . . .\n",
                          flags='NO NO YES', extra=sel)
        self.assertRaises(ValueError, rules.validate, StringIO("_foo.x a"))

    def test_validate_real_rules(self):
        """Test validation using rules similar to the IHM rules"""
        rules = make_rules("""
D1 conditional_presence ERROR entry . 'struct must be provided.' YES NO NO NO
D2 conditional_presence ERROR entity . 'entity_poly needed' YES NO NO NO
""", """
D1 1 THEN '_struct.entry_id' NOT_EMPTY . . . ANY .
D2 1 WHEN '_entity.type' EQ POLYMER . AND . .
D2 2 WHEN '_struct.pdbx_structure_determination_methodology' EQ integrative . AND ANY .
D2 3 THEN '_entity_poly.entity_id' NOT_EMPTY . . . ANY .
""")  # noqa: E501
        cif = """
_entry.id test
_struct.entry_id test
_struct.pdbx_structure_determination_methodology integrative
loop_
_entity.id
_entity.type
1 polymer
2 non-polymer
"""
        self.assertEqual(run_validate(rules, cif), [('D2', 'entity row 1')])
        self.assertEqual(run_validate(rules, cif + "_entity_poly.entity_id 1"),
                         [])
        self.assertEqual(run_validate(rules, "_entry.id test"),
                         [('D1', 'entry row 1')])

    def test_validate_binary_cif(self):
        """Test validation of BinaryCIF input"""
        sys.modules['msgpack'] = MockMsgPack
        rules = make_rule('foo', "R1 1 THEN '_foo.x' EQ ok . . . .\n")
        fh = MockFh()
        writer = ihm.format_bcif.BinaryCifWriter(fh)
        writer.start_block('ihm')
        with writer.loop('_foo', ['x']) as lp:
            lp.write(x='ok')
            lp.write(x='bad')
            lp.write(x=None)
        writer.flush()
        if _format:
            bio = BytesIO()
            _add_msgpack(fh.data, bio)
            bio.seek(0)
            fh.data = bio
        with self.assertRaises(ihm.deposition.RuleError) as cm:
            rules.validate(fh.data, format='BCIF')
        self.assertEqual([v.row for v in cm.exception.violations],
                         ['foo row 2'])


if __name__ == '__main__':
    unittest.main()
