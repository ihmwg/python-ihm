"""Classes to read in and apply a set of deposition rules.

   Deposition rules describe constraints on the content of an mmCIF file
   that go beyond what can be expressed in an mmCIF dictionary, such as
   requiring that certain categories be present only when some condition
   holds (for example, that ``ihm_3dem_restraint`` be provided if a
   dataset of type '3DEM volume' is present). The rules themselves are
   stored in mmCIF (or BinaryCIF) format, using the ``pdbx_deposition_rule``
   family of categories defined in the
   `deposition rules extension dictionary <https://github.com/ihmwg/IHMCIF/blob/master/extensions/mmcif_pdbx_deposition_rules_ext.dic>`_.

   See :func:`read` to read a set of rules from a file, and
   :meth:`Rules.validate` to check an mmCIF or BinaryCIF file against
   those rules.
"""  # noqa: E501

import ihm
import ihm.format
import ihm.format_bcif
import ihm.dictionary
from ihm.reader import Handler
import operator
import collections
import itertools
import warnings
import re


class RuleError(ihm.dictionary.ValidatorError):
    """Exception raised if a file violates one or more deposition rules
       with severity ERROR. See :meth:`Rules.validate`.

       The violations themselves are available as the `violations`
       attribute (a list of :class:`Violation` objects)."""
    def __init__(self, violations):
        self.violations = violations
        super().__init__("\n\n".join(str(v) for v in violations))


class RuleWarning(ihm.dictionary.ValidatorWarning):
    """Warning emitted if a file violates a deposition rule with severity
       WARNING. See :meth:`Rules.validate`.

       The violation itself is available as the `violation` attribute
       (a :class:`Violation` object)."""
    def __init__(self, violation):
        self.violation = violation
        super().__init__(str(violation))


class RuleInfo(RuleWarning):
    """Warning emitted if a file violates a deposition rule with severity
       INFO. These are typically suggestions for data that is relevant
       and should be provided if available. See :meth:`Rules.validate`."""
    pass


class UnsupportedRuleWarning(UserWarning):
    """Warning emitted for a deposition rule that cannot be evaluated by
       this module, for example a rule of the ``procedural`` family."""
    pass


# Special values for data items ('.', '?', or missing entirely)
class _CifSpecialValue:
    pass


class _NotInFileCif(_CifSpecialValue):
    pass


class _OmittedCif(_CifSpecialValue):
    pass


class _UnknownCif(_CifSpecialValue):
    pass


_NOT_IN_FILE = _NotInFileCif()


def _parse_item_name(name):
    """Split a full item name (e.g. '_entity.id') into lowercase
       (category, keyword) components"""
    name = name.strip()
    if name.startswith('_'):
        name = name[1:]
    cat, key = name.split('.', 1)
    return cat.lower(), key.lower()


def _split_csv(value):
    """Split a comma-separated list of values. A single space after each
       comma is permitted and is not part of the following value."""
    return re.split(r', ?', value)


def _split_item_names(value):
    """Split a comma-separated list of item names"""
    if value is None:
        return []
    return [_parse_item_name(x) for x in value.split(',') if x.strip()]


def _is_blank(raw):
    return isinstance(raw, _CifSpecialValue) or raw.strip() in ('', '?', '.')


class Condition:
    """A single WHEN, THEN or UNLESS condition of a :class:`Rule`."""
    def __init__(self, ordinal, role, item_name, operator, value=None,
                 compare_item_name=None, group_operator=None,
                 quantifier=None, value_transform=None):
        #: Ordinal (used to sort conditions)
        self.ordinal = ordinal
        #: The role of the condition: WHEN, THEN, or UNLESS
        self.role = role
        #: Full name of the item tested (e.g. '_entity.type')
        self.item_name = item_name
        #: Operator (e.g. EQ, NOT_EMPTY, GE_ITEM)
        self.operator = operator
        #: Value (or comma-separated list of values) to compare with,
        #: or None
        self.value = value
        #: Full name of the second item to compare with, or None
        self.compare_item_name = compare_item_name
        #: Operator used to combine conditions with the same role
        #: (AND or OR), or None for the default (AND)
        self.group_operator = group_operator
        #: Quantifier (ALL or ANY) applied over partner rows, or None
        #: for the default (ANY for WHEN and UNLESS, ALL for THEN)
        self.quantifier = quantifier
        #: Transformation (e.g. ABS) applied to item values before
        #: comparison, or None
        self.value_transform = value_transform

    def _get_quantifier(self):
        if self.quantifier:
            return self.quantifier
        return 'ALL' if self.role == 'THEN' else 'ANY'


class Join:
    """Description of how rows of a :class:`Rule`'s scope category are
       paired with rows of a partner category."""
    def __init__(self, ordinal, scope_item_names, partner_item_names,
                 on_no_match=None):
        #: Ordinal (used to sort joins)
        self.ordinal = ordinal
        #: Comma-separated list of item names in the scope category
        self.scope_item_names = scope_item_names
        #: Comma-separated list of item names in the partner category
        self.partner_item_names = partner_item_names
        #: Action when a scope row has no partner: SKIP (the default),
        #: FAIL, or SINGLE_ROW_FALLBACK
        self.on_no_match = on_no_match or 'SKIP'


class RowSelection:
    """Restriction of the rows of a category on which a :class:`Rule`
       is evaluated."""
    def __init__(self, category_id, selector, selector_item=None,
                 group_by=None, exclude_items=None):
        #: Category whose rows are restricted
        self.category_id = category_id
        #: Selection method (MIN, MAX, or ANY_VALUE)
        self.selector = selector
        #: Full name of the item used to rank rows (for MIN and MAX)
        self.selector_item = selector_item
        #: Comma-separated list of item names used to partition rows
        #: into groups, or None
        self.group_by = group_by
        #: Comma-separated list of item names ignored by ANY_VALUE, or None
        self.exclude_items = exclude_items


class Rule:
    """A single deposition rule in a :class:`Rules` object."""
    def __init__(self, id, family, severity, scope_category, message,
                 procedural_method=None, enabled=True, param_flag=False,
                 join_flag=False, row_selection_flag=False):
        #: Unique identifier
        self.id = id
        #: Rule family (e.g. conditional_presence, pairwise_order)
        self.family = family
        #: Rule severity (ERROR, WARNING, or INFO)
        self.severity = severity
        #: Category in which each violation is assessed and reported
        self.scope_category = scope_category
        #: Human-readable message reported when the rule is violated
        self.message = message
        #: Name of the built-in check, for procedural rules
        self.procedural_method = procedural_method
        #: True iff the rule should be checked
        self.enabled = enabled
        #: True iff the rule's parameters (:attr:`params`) are used
        self.param_flag = param_flag
        #: True iff the rule's joins (:attr:`joins`) are used
        self.join_flag = join_flag
        #: True iff the rule's row selections (:attr:`row_selections`)
        #: are used
        self.row_selection_flag = row_selection_flag
        #: List of :class:`Condition` objects, sorted by ordinal
        self.conditions = []
        #: Mapping from name to value of extra parameters
        self.params = {}
        #: List of :class:`Join` objects, sorted by ordinal
        self.joins = []
        #: List of :class:`RowSelection` objects
        self.row_selections = []


class Violation:
    """A violation of a single :class:`Rule` by a file.
       See :meth:`Rules.validate`."""
    def __init__(self, rule, data_block, row, detail=None):
        #: The :class:`Rule` that was violated
        self.rule = rule
        #: Index (starting at 1) of the data block in the file
        self.data_block = data_block
        #: Description of the scope row (or group of rows) that violated
        #: the rule
        self.row = row
        #: Additional detail about the violation, or None
        self.detail = detail

    severity = property(lambda self: self.rule.severity)

    def __str__(self):
        s = "%s %s: %s" % (self.rule.severity, self.rule.id,
                           self.rule.message)
        loc = self.row
        if self.data_block > 1:
            loc = "data block %d, %s" % (self.data_block, loc)
        s += " [%s]" % loc
        if self.detail:
            s += " (%s)" % self.detail
        return s


class Rules:
    """Representation of a set of deposition rules.
       See :func:`read` to create a Rules object from a file.

       Multiple Rules objects can be added together to yield a Rules
       object that includes all the rules in the originals."""
    def __init__(self):
        #: Mapping from ID to :class:`Rule` objects
        self.rules = {}

    def __iadd__(self, other):
        self.rules.update(other.rules)
        return self

    def __add__(self, other):
        r = Rules()
        r += self
        r += other
        return r

    def validate(self, fh, format='mmCIF', dictionary=None):
        """Validate the given file against these deposition rules.

           Each data block in the file is checked independently against
           every enabled rule. A violation of a rule with severity ERROR is
           collected and, once the entire file has been checked, a
           :class:`RuleError` containing all such violations is raised.
           Violations of rules with severity WARNING or INFO are reported
           by emitting a :class:`RuleWarning` or :class:`RuleInfo` warning
           respectively, using the Python :mod:`warnings` module.

           Rules that cannot be evaluated by this module (procedural rules,
           or aggregate rules that use an unsupported aggregate function)
           are skipped with an :class:`UnsupportedRuleWarning`.

           Rules compare values using the item types defined in the main
           mmCIF dictionary. If no dictionary is provided, values that look
           like numbers are compared numerically, and all other values are
           compared without regard to case. If a dictionary is provided,
           values are compared according to their item type (e.g. values
           with a `ucode` type are compared case-insensitively, while those
           with a `code` type are compared case-sensitively) and values that
           do not match their item type are treated as missing. The
           dictionary is also required for the MATCHES_TYPE and
           IN_ENUMERATION_DETAILS_OF operators, and to determine which
           items are present in a category for ANY_VALUE row selection;
           without it, these comparisons are skipped.

           If a rule's scope category is entirely absent from the file,
           the rule is evaluated once for a single notional row in which
           every item is absent. This allows rules such as
           "``entry`` must be provided" to be checked.

           :param file fh: The file handle to read from.
           :param str format: The format of the file. This can be 'mmCIF'
              (the default) for the (text-based) mmCIF format or 'BCIF' for
              BinaryCIF.
           :param dictionary: The main mmCIF dictionary that describes
              the file (usually PDBx plus extensions such as IHM).
           :type dictionary: :class:`ihm.dictionary.Dictionary`
           :return: A list of all :class:`Violation` objects (if no
              errors were found).
           :raises: :class:`RuleError` if the file violates any rule
              with severity ERROR.
        """
        reader_map = {'mmCIF': ihm.format.CifReader,
                      'BCIF': ihm.format_bcif.BinaryCifReader}
        rules = [r for r in self.rules.values() if r.enabled]
        for r in rules:
            reason = _get_unsupported_reason(r)
            if reason:
                warnings.warn("Deposition rule %s cannot be checked: %s"
                              % (r.id, reason), UnsupportedRuleWarning,
                              stacklevel=2)
        rules = [r for r in rules if not _get_unsupported_reason(r)]
        store = _DataStore()
        handlers = [_DataHandler(store, cat, keys)
                    for cat, keys in _get_needed_keys(rules,
                                                      dictionary).items()]
        rd = reader_map[format](
            fh, dict((h.category, h) for h in handlers),
            unknown_keyword_handler=_UnknownKeywordHandler(store))
        violations = []
        block = 0
        more_data = True
        while more_data:
            more_data = rd.read_file()
            block += 1
            store.finalize_block()
            ev = _Evaluator(store.tables, dictionary)
            for rule in rules:
                for row, detail in ev.check_rule(rule):
                    violations.append(Violation(rule, block, row, detail))
            store.reset()
        for v in violations:
            sev = v.severity.upper() if v.severity else ''
            if sev == 'WARNING':
                warnings.warn(RuleWarning(v), stacklevel=2)
            elif sev != 'ERROR':
                warnings.warn(RuleInfo(v), stacklevel=2)
        errors = [v for v in violations
                  if v.severity and v.severity.upper() == 'ERROR']
        if errors:
            raise RuleError(errors)
        return violations


_supported_aggregates = frozenset(['SUM'])


def _get_unsupported_reason(rule):
    """Return a reason why the rule cannot be evaluated, or None"""
    family = rule.family.lower() if rule.family else ''
    if family == 'procedural':
        return ("procedural rules (method %s) are not supported"
                % rule.procedural_method)
    if family == 'aggregate':
        agg = rule.params.get('aggregate', '').upper()
        if agg not in _supported_aggregates:
            return "aggregate function %s is not supported" % agg
    if not any(c.role == 'THEN' for c in rule.conditions):
        return "rule has no THEN condition"


def _get_needed_keys(rules, dictionary):
    """Get a mapping from category name to the set of keywords in that
       category that are needed to evaluate the given rules"""
    keys = collections.defaultdict(set)

    def add_item(name):
        if name:
            cat, key = _parse_item_name(name)
            keys[cat].add(key)

    def add_items(names):
        for cat, key in _split_item_names(names):
            keys[cat].add(key)

    for rule in rules:
        keys[rule.scope_category.lower()]
        for c in rule.conditions:
            add_item(c.item_name)
            add_item(c.compare_item_name)
        if rule.param_flag:
            add_items(rule.params.get('group_by'))
        if rule.join_flag:
            for j in rule.joins:
                add_items(j.scope_item_names)
                add_items(j.partner_item_names)
        if rule.row_selection_flag:
            for rs in rule.row_selections:
                cat = rs.category_id.lower()
                keys[cat]
                add_item(rs.selector_item)
                add_items(rs.group_by)
                if (rs.selector.upper() == 'ANY_VALUE'
                        and dictionary is not None
                        and cat in dictionary.categories):
                    keys[cat] |= set(
                        dictionary.categories[cat].keywords.keys())
    return keys


class _DataStore:
    """Data read from a single data block of the file being validated"""
    def __init__(self):
        self.reset()

    def reset(self):
        #: Mapping from category name to list of rows (dicts)
        self.tables = {}
        #: Names of categories seen that contain keywords we didn't ask for
        self.seen_categories = set()

    def finalize_block(self):
        # The reader does not call a handler for a non-looped category that
        # contains none of the keywords we asked for. Such a category is
        # still present in the file, so give it a single row in which
        # every requested keyword is absent.
        for cat in self.seen_categories:
            if cat not in self.tables:
                self.tables[cat] = [{}]


class _UnknownKeywordHandler:
    """Note categories that contain keywords not needed by the rules"""
    def __init__(self, store):
        self.store = store

    def __call__(self, catname, keyname, line):
        self.store.seen_categories.add(catname.lstrip('_').lower())


class _DataHandler(Handler):
    """Read every row of a category, as a dict of keyword: raw value"""
    not_in_file = _NOT_IN_FILE
    omitted = _OmittedCif()
    unknown = _UnknownCif()

    def __init__(self, sysr, category, keys):
        super().__init__(sysr)
        self.category = '_' + category
        self._cat = category
        self._keys = sorted(keys)

    def __call__(self, *args):
        tables = self.sysr.tables
        if self._cat not in tables:
            tables[self._cat] = []
        tables[self._cat].append(dict(zip(self._keys, args)))


class _Value:
    """A non-missing value of a data item, for comparisons"""
    __slots__ = ['raw', 'num', 'key']

    def __init__(self, raw, item_type):
        self.raw = raw
        self.num = None
        if item_type is None or item_type.primitive_code == 'numb':
            # Remove any standard uncertainty, e.g. 1.234(5)
            try:
                self.num = float(re.sub(r'\([0-9]+\)$', '', raw))
            except ValueError:
                pass
        if item_type is not None and item_type.case_sensitive:
            self.key = raw
        else:
            self.key = raw.upper()

    def norm(self):
        """Get a hashable representation, used for equality tests"""
        return self.key if self.num is None else self.num


def _cmp(a, b):
    """Compare two _Value objects, returning -1, 0 or 1"""
    if a.num is not None and b.num is not None:
        x, y = a.num, b.num
    else:
        x, y = a.key, b.key
    return (x > y) - (x < y)


_cmp_ops = {'EQ': operator.eq, 'NE': operator.ne, 'LT': operator.lt,
            'LE': operator.le, 'GT': operator.gt, 'GE': operator.ge}
_item_cmp_ops = {'EQ_ITEM': operator.eq, 'LT_ITEM': operator.lt,
                 'LE_ITEM': operator.le, 'GT_ITEM': operator.gt,
                 'GE_ITEM': operator.ge}
_unary_ops = frozenset(['EXISTS', 'NOT_EXISTS', 'EMPTY', 'NOT_EMPTY'])
# Operators where compare_item_name is not taken from partner rows
_no_partner_ops = frozenset(['IN_COLUMN_OF', 'IN_ENUMERATION_DETAILS_OF'])


class _Skip(Exception):
    """Raised if a scope row should not be evaluated"""
    pass


class _JoinFailed(Exception):
    """Raised if a scope row has no partner and the join requests FAIL"""
    pass


class _Evaluator:
    """Evaluate rules against the data from a single data block"""
    def __init__(self, tables, dictionary):
        self.tables = tables
        self.dictionary = dictionary
        self._regex_cache = {}

    def _get_keyword(self, cat, key):
        if self.dictionary is None:
            return None
        c = self.dictionary.categories.get(cat)
        if c is not None:
            return c.keywords.get(key)

    def _get_item_type(self, cat, key):
        k = self._get_keyword(cat, key)
        if k is not None:
            return k.item_type

    def get_value(self, cat, key, row, transform=None):
        """Get the value of the given item in the given row as a _Value,
           or None if it is missing"""
        raw = row.get(key, _NOT_IN_FILE)
        if _is_blank(raw):
            return None
        raw = raw.strip()
        item_type = self._get_item_type(cat, key)
        if item_type is not None and not item_type.regex.match(raw):
            # Values that don't match their type are treated as missing
            return None
        v = _Value(raw, item_type)
        if transform and transform.upper() == 'ABS':
            if v.num is None:
                return None
            v.num = abs(v.num)
        return v

    def _get_regex(self, regex):
        if regex not in self._regex_cache:
            self._regex_cache[regex] = re.compile(regex)
        return self._regex_cache[regex]

    def check_rule(self, rule):
        """Check the given rule. Yield a (row, detail) tuple
           for each violation."""
        return _RuleChecker(self, rule).check()


class _RuleChecker:
    """Evaluate a single rule against the data from a single data block"""
    def __init__(self, ev, rule):
        self.ev = ev
        self.rule = rule
        self.scope = rule.scope_category.lower()
        self.conditions = {'WHEN': [], 'THEN': [], 'UNLESS': []}
        for c in rule.conditions:
            role = c.role.upper()
            if role not in self.conditions:
                raise ValueError("Unknown role %s for rule %s"
                                 % (c.role, rule.id))
            self.conditions[role].append(c)
        self._selected = {}
        self._column_cache = {}
        self._unique_cache = {}

    def get_rows(self, cat):
        """Get all rows of the given category, after row selection"""
        if cat not in self._selected:
            rows = self.ev.tables.get(cat, [])
            if self.rule.row_selection_flag:
                for rs in self.rule.row_selections:
                    if rs.category_id.lower() == cat:
                        rows = self._select_rows(rs, cat, rows)
            self._selected[cat] = rows
        return self._selected[cat]

    def _select_rows(self, rs, cat, rows):
        selector = rs.selector.upper()
        if selector == 'ANY_VALUE':
            exclude = set(key for c, key in _split_item_names(
                rs.exclude_items) if c == cat)
            present = set()
            for row in rows:
                present.update(k for k, v in row.items()
                               if not isinstance(v, _NotInFileCif))
            keys = present - exclude
            return [row for row in rows
                    if any(not _is_blank(row[k]) for k in keys)]
        elif selector in ('MIN', 'MAX'):
            scat, skey = _parse_item_name(rs.selector_item)
            group_by = _split_item_names(rs.group_by)
            groups = collections.OrderedDict()
            for row in rows:
                v = self.ev.get_value(scat, skey, row)
                if v is None:
                    continue
                g = tuple(self._norm(c, k, row) for c, k in group_by)
                groups.setdefault(g, []).append((v, row))
            best_sign = -1 if selector == 'MIN' else 1
            selected = []
            for g in groups.values():
                best = g[0][0]
                for v, row in g:
                    if _cmp(v, best) == best_sign:
                        best = v
                selected.extend(row for v, row in g if _cmp(v, best) == 0)
            # Preserve original row order
            selected_ids = set(id(r) for r in selected)
            return [r for r in rows if id(r) in selected_ids]
        else:
            raise ValueError("Unknown row selector %s for rule %s"
                             % (rs.selector, self.rule.id))

    def _norm(self, cat, key, row):
        v = self.ev.get_value(cat, key, row)
        return None if v is None else v.norm()

    def get_scope_rows(self):
        """Get all rows of the scope category, as (description, row)"""
        if self.scope not in self.ev.tables:
            # If the scope category is absent, evaluate a single
            # notional row in which every item is absent
            return [("%s category is absent" % self.scope, {})]
        else:
            selected = set(id(r) for r in self.get_rows(self.scope))
            return [("%s row %d" % (self.scope, i + 1), row)
                    for i, row in enumerate(self.ev.tables[self.scope])
                    if id(row) in selected]

    def _get_partner_categories(self):
        cats = set()
        for c in self.rule.conditions:
            cats.add(_parse_item_name(c.item_name)[0])
            if (c.compare_item_name
                    and c.operator.upper() not in _no_partner_ops):
                cats.add(_parse_item_name(c.compare_item_name)[0])
        cats.discard(self.scope)
        return cats

    def _get_join_partners(self, join, srow):
        """Get partner rows for the given scope row and join"""
        scope_items = _split_item_names(join.scope_item_names)
        partner_items = _split_item_names(join.partner_item_names)
        pcat = partner_items[0][0]
        prows = self.get_rows(pcat)
        svals = [self._norm(c, k, srow) for c, k in scope_items]
        if None not in svals:
            svals = tuple(svals)
            partners = [p for p in prows
                        if tuple(self._norm(c, k, p)
                                 for c, k in partner_items) == svals]
        else:
            partners = []
        if partners:
            return pcat, partners
        on_no_match = join.on_no_match.upper()
        if on_no_match == 'FAIL':
            raise _JoinFailed("no matching row in %s" % pcat)
        elif on_no_match == 'SINGLE_ROW_FALLBACK':
            absent = (None in svals
                      or all(None in [self._norm(c, k, p)
                                      for c, k in partner_items]
                             for p in prows))
            if (absent and len(prows) == 1
                    and len(self.get_rows(self.scope)) == 1):
                return pcat, prows
        raise _Skip()

    def get_partners(self, srow):
        """Get a mapping from partner category to partner rows for the
           given scope row"""
        partners = {}
        if self.rule.join_flag:
            for j in self.rule.joins:
                pcat, prows = self._get_join_partners(j, srow)
                partners[pcat] = prows
        for cat in self._get_partner_categories():
            if cat not in partners:
                partners[cat] = self.get_rows(cat)
        return partners

    def check(self):
        if self.rule.family.lower() == 'aggregate':
            yield from self._check_aggregate()
            return
        for desc, srow in self.get_scope_rows():
            try:
                partners = self.get_partners(srow)
                if not self._applies(srow, partners):
                    continue
                if not self._combine('THEN', srow, partners):
                    yield desc, None
            except _Skip:
                pass
            except _JoinFailed as err:
                yield desc, str(err)

    def _applies(self, srow, partners):
        """Return True iff the rule applies to the given scope row"""
        if (self.conditions['WHEN']
                and not self._combine('WHEN', srow, partners)):
            return False
        return not (self.conditions['UNLESS']
                    and self._combine('UNLESS', srow, partners))

    def _check_aggregate(self):
        group_by = _split_item_names(self.rule.params.get('group_by'))
        groups = collections.OrderedDict()
        for desc, srow in self.get_scope_rows():
            try:
                partners = self.get_partners(srow)
                if self._applies(srow, partners):
                    g = tuple(self._norm(c, k, srow) for c, k in group_by)
                    groups.setdefault(g, []).append((srow, partners))
            except (_Skip, _JoinFailed):
                pass
        # Only SUM is currently supported
        for gkey, rows in groups.items():
            # Make a notional row containing the sum of each item that
            # is tested by a THEN condition
            agg_row = dict(rows[0][0])
            for c in self.conditions['THEN']:
                cat, key = _parse_item_name(c.item_name)
                if cat != self.scope:
                    continue
                vals = [self.ev.get_value(cat, key, row) for row, _ in rows]
                vals = [v.num for v in vals if v is not None
                        and v.num is not None]
                agg_row[key] = repr(sum(vals)) if vals else _NOT_IN_FILE
            if not self._combine('THEN', agg_row, rows[0][1]):
                first = rows[0][0]
                desc = ", ".join(
                    "%s.%s=%s" % (c, k, self.ev.get_value(c, k, first).raw
                                  if g is not None else '?')
                    for (c, k), g in zip(group_by, gkey))
                yield ("group of %d %s rows (%s)"
                       % (len(rows), self.scope, desc)), None

    def _combine(self, role, srow, partners):
        """Evaluate and combine all conditions with the given role"""
        conds = self.conditions[role]
        group_op = 'AND'
        for c in conds:
            if c.group_operator:
                group_op = c.group_operator.upper()
                break
        # A condition that cannot be evaluated (due to missing values) is
        # treated as not holding for WHEN and UNLESS, but satisfied for THEN
        skip_value = role == 'THEN'
        results = (self._eval_condition(c, srow, partners) for c in conds)
        results = (skip_value if r is None else r for r in results)
        return any(results) if group_op == 'OR' else all(results)

    def _quantify(self, results, cond):
        if cond._get_quantifier().upper() == 'ALL':
            return all(results)
        else:
            return any(results)

    def _get_cond_rows(self, cat, srow, partners):
        return [srow] if cat == self.scope else partners.get(cat, [])

    def _eval_condition(self, cond, srow, partners):
        """Evaluate a single condition for the given scope row.
           Return True or False, or None if the condition could not be
           evaluated."""
        op = cond.operator.upper()
        icat, ikey = _parse_item_name(cond.item_name)
        if op in _unary_ops:
            results = [self._eval_unary(op, icat, ikey, row)
                       for row in self._get_cond_rows(icat, srow, partners)]
            if icat == self.scope:
                return results[0]
            return self._quantify(results, cond)
        if op in _item_cmp_ops:
            ccat, ckey = _parse_item_name(cond.compare_item_name)
            if icat == self.scope and ccat == self.scope:
                pairs = [(srow, srow)]
            elif icat == ccat:
                pairs = [(p, p) for p in partners.get(icat, [])]
            else:
                pairs = itertools.product(
                    self._get_cond_rows(icat, srow, partners),
                    self._get_cond_rows(ccat, srow, partners))
        else:
            rows = self._get_cond_rows(icat, srow, partners)
            pairs = [(r, r) for r in rows]
        results = [self._compare(op, cond, icat, ikey, r1, r2)
                   for r1, r2 in pairs]
        results = [r for r in results if r is not None]
        if not results:
            return None
        return self._quantify(results, cond)

    def _eval_unary(self, op, cat, key, row):
        if op == 'EXISTS':
            return not isinstance(row.get(key, _NOT_IN_FILE), _NotInFileCif)
        elif op == 'NOT_EXISTS':
            return isinstance(row.get(key, _NOT_IN_FILE), _NotInFileCif)
        empty = self.ev.get_value(cat, key, row) is None
        return empty if op == 'EMPTY' else not empty

    def _compare(self, op, cond, icat, ikey, row, crow):
        """Compare the value of item_name in `row` using the condition.
           Return True or False, or None if a comparison could not be
           made. `crow` is the row used to obtain the value of
           compare_item_name, if needed."""
        v = self.ev.get_value(icat, ikey, row, cond.value_transform)
        if v is None:
            return None
        item_type = self.ev._get_item_type(icat, ikey)
        if op in _cmp_ops:
            if cond.value is None:
                return None
            return _cmp_ops[op](_cmp(v, _Value(cond.value, item_type)), 0)
        elif op in ('IN', 'NOT_IN'):
            if cond.value is None:
                return None
            found = any(_cmp(v, _Value(x, item_type)) == 0
                        for x in _split_csv(cond.value))
            return found if op == 'IN' else not found
        elif op in ('MATCHES', 'NOT_MATCHES'):
            if cond.value is None:
                return None
            found = self.ev._get_regex(cond.value).search(v.raw) is not None
            return found if op == 'MATCHES' else not found
        elif op == 'MATCHES_TYPE':
            if self.ev.dictionary is None or cond.value is None:
                return None
            types = [self.ev.dictionary.item_types.get(t)
                     for t in _split_csv(cond.value)]
            types = [t for t in types if t is not None]
            if not types:
                return None
            return any(t.regex.match(v.raw) for t in types)
        elif op in _item_cmp_ops:
            ccat, ckey = _parse_item_name(cond.compare_item_name)
            cv = self.ev.get_value(ccat, ckey, crow, cond.value_transform)
            if cv is None:
                return None
            return _item_cmp_ops[op](_cmp(v, cv), 0)
        elif op == 'UNIQUE':
            return self._get_value_counts(icat, ikey)[v.norm()] == 1
        elif op == 'IN_COLUMN_OF':
            ccat, ckey = _parse_item_name(cond.compare_item_name)
            column = self._get_column(ccat, ckey)
            if not column:
                return None
            return v.norm() in column
        elif op == 'IN_ENUMERATION_DETAILS_OF':
            return self._in_enumeration_details(cond, v, item_type, crow)
        else:
            raise ValueError("Unknown operator %s for rule %s"
                             % (cond.operator, self.rule.id))

    def _get_value_counts(self, cat, key):
        if (cat, key) not in self._unique_cache:
            c = collections.Counter()
            for row in self.get_rows(cat):
                v = self.ev.get_value(cat, key, row)
                if v is not None:
                    c[v.norm()] += 1
            self._unique_cache[(cat, key)] = c
        return self._unique_cache[(cat, key)]

    def _get_column(self, cat, key):
        if (cat, key) not in self._column_cache:
            vals = (self.ev.get_value(cat, key, row)
                    for row in self.get_rows(cat))
            self._column_cache[(cat, key)] = frozenset(
                v.norm() for v in vals if v is not None)
        return self._column_cache[(cat, key)]

    def _in_enumeration_details(self, cond, v, item_type, crow):
        ccat, ckey = _parse_item_name(cond.compare_item_name)
        cv = self.ev.get_value(ccat, ckey, crow)
        kw = self.ev._get_keyword(ccat, ckey)
        if cv is None or kw is None or not kw.enumeration:
            return None
        details = getattr(kw.enumeration, 'details', {})
        detail = details.get(cv.raw)
        if detail is None and not getattr(kw.enumeration, 'case_sensitive',
                                          True):
            for enum_val, enum_detail in details.items():
                if enum_val.upper() == cv.raw.upper():
                    detail = enum_detail
                    break
        if detail is None:
            return None
        return any(_cmp(v, _Value(x.strip(), item_type)) == 0
                   for x in _split_csv(detail.strip()))


def _get_str(val):
    """Map omitted or unknown values to None"""
    return None if val is None or val is ihm.unknown else val


def _get_flag(val, default):
    """Map omitted or unknown bool values to the given default"""
    return default if val is None or val is ihm.unknown else val


def _get_ordinal(val):
    val = _get_str(val)
    try:
        return int(val)
    except (TypeError, ValueError):
        return val


class _RulesReader:
    """Track information for Rules being read from a file."""
    def __init__(self):
        self.rules = Rules()
        self.conditions = []
        self.params = []
        self.joins = []
        self.row_selections = []

    def _get_rule(self, rule_id, category):
        try:
            return self.rules.rules[rule_id]
        except KeyError:
            raise ValueError("%s refers to undefined deposition rule %s"
                             % (category, rule_id))

    def finalize(self):
        for rule_id, cond in self.conditions:
            r = self._get_rule(rule_id, 'pdbx_deposition_rule_condition')
            r.conditions.append(cond)
        for rule_id, name, value in self.params:
            r = self._get_rule(rule_id, 'pdbx_deposition_rule_param')
            r.params[name] = value
        for rule_id, join in self.joins:
            r = self._get_rule(rule_id, 'pdbx_deposition_rule_join')
            r.joins.append(join)
        for rule_id, rs in self.row_selections:
            r = self._get_rule(rule_id, 'pdbx_deposition_rule_row_selection')
            r.row_selections.append(rs)

        def sort_key(x):
            # Sort integer ordinals before any non-integer ones
            return ((0, x.ordinal, '') if isinstance(x.ordinal, int)
                    else (1, 0, str(x.ordinal)))
        for r in self.rules.rules.values():
            r.conditions.sort(key=sort_key)
            r.joins.sort(key=sort_key)


class _RuleHandler(Handler):
    category = '_pdbx_deposition_rule'

    def __call__(self, id, family, severity, scope_category,
                 procedural_method, message, enabled: bool,
                 param_flag: bool, join_flag: bool,
                 row_selection_flag: bool):
        severity = _get_str(severity)
        r = Rule(id=id, family=_get_str(family),
                 severity=severity.upper() if severity else None,
                 scope_category=_get_str(scope_category),
                 message=_get_str(message),
                 procedural_method=_get_str(procedural_method),
                 enabled=_get_flag(enabled, True),
                 param_flag=_get_flag(param_flag, False),
                 join_flag=_get_flag(join_flag, False),
                 row_selection_flag=_get_flag(row_selection_flag, False))
        self.sysr.rules.rules[r.id] = r


class _ConditionHandler(Handler):
    category = '_pdbx_deposition_rule_condition'

    def __call__(self, rule_id, ordinal, role, item_name, operator, value,
                 compare_item_name, group_operator, quantifier,
                 value_transform):
        role = _get_str(role)
        c = Condition(ordinal=_get_ordinal(ordinal),
                      role=role.upper() if role else None,
                      item_name=_get_str(item_name),
                      operator=_get_str(operator),
                      value=_get_str(value),
                      compare_item_name=_get_str(compare_item_name),
                      group_operator=_get_str(group_operator),
                      quantifier=_get_str(quantifier),
                      value_transform=_get_str(value_transform))
        self.sysr.conditions.append((rule_id, c))


class _ParamHandler(Handler):
    category = '_pdbx_deposition_rule_param'

    def __call__(self, rule_id, name, value):
        self.sysr.params.append((rule_id, name, _get_str(value)))


class _JoinHandler(Handler):
    category = '_pdbx_deposition_rule_join'

    def __call__(self, rule_id, ordinal, scope_item_names,
                 partner_item_names, on_no_match):
        j = Join(ordinal=_get_ordinal(ordinal),
                 scope_item_names=_get_str(scope_item_names),
                 partner_item_names=_get_str(partner_item_names),
                 on_no_match=_get_str(on_no_match))
        self.sysr.joins.append((rule_id, j))


class _RowSelectionHandler(Handler):
    category = '_pdbx_deposition_rule_row_selection'

    def __call__(self, rule_id, category_id, selector, selector_item,
                 group_by, exclude_items):
        rs = RowSelection(category_id=_get_str(category_id),
                          selector=_get_str(selector),
                          selector_item=_get_str(selector_item),
                          group_by=_get_str(group_by),
                          exclude_items=_get_str(exclude_items))
        self.sysr.row_selections.append((rule_id, rs))


def read(fh, format='mmCIF'):
    """Read deposition rules from the given file handle.

       :param file fh: The file handle to read from.
       :param str format: The format of the file. This can be 'mmCIF' (the
          default) for the (text-based) mmCIF format or 'BCIF' for
          BinaryCIF.
       :return: The deposition rules.
       :rtype: :class:`Rules`
    """
    reader_map = {'mmCIF': ihm.format.CifReader,
                  'BCIF': ihm.format_bcif.BinaryCifReader}
    s = _RulesReader()
    handlers = [_RuleHandler(s), _ConditionHandler(s), _ParamHandler(s),
                _JoinHandler(s), _RowSelectionHandler(s)]
    r = reader_map[format](fh, dict((h.category, h) for h in handlers))
    # Read all data blocks
    while r.read_file():
        pass
    s.finalize()
    return s.rules
