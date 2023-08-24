"""Helper classes to provide a summary report of an :class:`ihm.System`"""

from __future__ import print_function
import ihm
import sys
import warnings
import collections


class MissingDataWarning(UserWarning):
    pass


class _SectionReporter(object):
    def __init__(self, title, fh):
        self.fh = fh
        print("\n\n# " + title, file=self.fh)

    def report(self, txt):
        print("   " + str(txt), file=self.fh)


class Reporter(object):
    def __init__(self, system, fh=sys.stdout):
        self.system = system
        self.fh = fh

    def report(self):
        print("Title: %s" % self.system.title, file=self.fh)
        self.report_entities()
        self.report_asyms()
        self.report_citations()
        self.report_software()

    def _section(self, title):
        return _SectionReporter(title, self.fh)

    def report_entities(self):
        r = self._section("Entities (unique sequences)")
        asyms_for_entity = collections.defaultdict(list)
        for a in self.system.asym_units:
            asyms_for_entity[a.entity].append(a)
        for e in self.system.entities:
            asyms = asyms_for_entity[e]
            r.report("- %s (length %d, %d instances, chain IDs %s)"
                     % (e.description, len(e.sequence), len(asyms),
                        ", ".join(a.id for a in asyms)))
            if len(e.references) == 0:
                warnings.warn(
                    "No reference sequence (e.g. from UniProt) provided "
                    "for %s" % e, MissingDataWarning)
            for ref in e.references:
                r.report("  - from %s" % str(ref))

    def report_asyms(self):
        r = self._section("Asyms/chains")
        for a in self.system.asym_units:
            r.report("- %s (chain ID %s)" % (a.details, a.id))

    def report_citations(self):
        r = self._section("Publications cited")
        for c in self.system._all_citations():
            r.report('- "%s", %s, %s' % (c.title, c.journal, c.year))

    def report_software(self):
        r = self._section("Software used")
        for s in ihm._remove_identical(self.system._all_software()):
            r.report("- %s (version %s)" % (s.name, s.version))
            if not s.citation:
                warnings.warn(
                    "No citation provided for %s" % s, MissingDataWarning)
