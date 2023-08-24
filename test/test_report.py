import unittest
import utils
import os
import sys
if sys.version_info[0] >= 3:
    from io import StringIO
else:
    from io import BytesIO as StringIO

TOPDIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
utils.set_search_paths(TOPDIR)
import ihm
import ihm.report
import ihm.reference


class Tests(unittest.TestCase):
    def test_report(self):
        """Test System.report()"""
        sio = StringIO()
        s = ihm.System(title='test system')
        s.report(sio)

    def test_entities(self):
        """Test report_entities"""
        sio = StringIO()
        s = ihm.System(title='test system')
        e = ihm.Entity("ACG")
        s.entities.append(e)
        r = ihm.report.Reporter(s, sio)
        # Should warn about missing references
        self.assertWarns(ihm.report.MissingDataWarning, r.report_entities)
        uniprot = ihm.reference.UniProtSequence(
            db_code='testcode', accession='testacc', sequence='CCCG')
        e.references.append(uniprot)
        r.report_entities()

    def test_asyms(self):
        """Test report_asyms"""
        sio = StringIO()
        s = ihm.System(title='test system')
        e = ihm.Entity("ACG")
        s.entities.append(e)
        a = ihm.AsymUnit(e, "my asym")
        s.asym_units.append(a)
        r = ihm.report.Reporter(s, sio)
        r.report_asyms()

    def test_citations(self):
        """Test report_citations"""
        sio = StringIO()
        s = ihm.System(title='test system')
        c = ihm.Citation(pmid="foo", title="bar", journal="j", volume=1,
                         page_range=(10, 20), year=2023,
                         authors=["foo", "bar"], doi="test")
        s.citations.append(c)
        r = ihm.report.Reporter(s, sio)
        r.report_citations()

    def test_software(self):
        """Test report_software"""
        sio = StringIO()
        s = ihm.System(title='test system')
        soft = ihm.Software(name='foo', version='1.0',
                            classification='1', description='2', location='3')
        s.software.append(soft)
        r = ihm.report.Reporter(s, sio)
        # Should warn about missing citation
        self.assertWarns(ihm.report.MissingDataWarning, r.report_software)
        c = ihm.Citation(pmid="foo", title="bar", journal="j", volume=1,
                         page_range=(10, 20), year=2023,
                         authors=["foo", "bar"], doi="test")
        soft.citation = c
        r.report_software()


if __name__ == '__main__':
    unittest.main()
