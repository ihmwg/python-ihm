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
import ihm.reader

class Tests(unittest.TestCase):
    def test_read(self):
        """Test read() function"""
        fh = StringIO("data_model\n_struct.entry_id testid\n")
        s, = ihm.reader.read(fh)
        self.assertEqual(s.id, 'testid')

    def test_system_reader(self):
        """Test SystemReader class"""
        s = ihm.reader._SystemReader()

    def test_id_mapper(self):
        """Test IDMapper class"""
        class MockObject(object):
            def __init__(self, x, y):
                self.x, self.y = x, y

        testlist = []
        im = ihm.reader._IDMapper(testlist, MockObject, '_id', '1', y='2')
        a = im.get_by_id('ID1')
        b = im.get_by_id('ID1')
        self.assertEqual(id(a), id(b))
        self.assertEqual(a.x, '1')
        self.assertEqual(a.y, '2')
        self.assertEqual(testlist, [a])

    def test_handler(self):
        """Test Handler base class"""
        class MockObject(object):
            pass
        o = MockObject()
        o.system = 'foo'
        h = ihm.reader._Handler(o)
        self.assertEqual(h.system, 'foo')

    def test_handler_copy_if_present(self):
        """Test copy_if_present method"""
        class MockObject(object):
            pass
        o = MockObject()
        h = ihm.reader._Handler(None)
        h._copy_if_present(o, {'foo':'bar', 'bar':'baz', 't':'u'},
                           keys=['test', 'foo'],
                           mapkeys={'bar':'baro', 'x':'y'})
        self.assertEqual(o.foo, 'bar')
        self.assertEqual(o.baro, 'baz')
        self.assertFalse(hasattr(o, 't'))
        self.assertFalse(hasattr(o, 'x'))
        self.assertFalse(hasattr(o, 'bar'))

    def test_struct_handler(self):
        """Test StructHandler"""
        fh = StringIO("_struct.entry_id eid\n_struct.title 'Test title'")
        s, = ihm.reader.read(fh)
        self.assertEqual(s.id, 'eid')
        self.assertEqual(s.title, 'Test title')

    def test_software_handler(self):
        """Test SoftwareHandler"""
        fh = StringIO("""
loop_
_software.pdbx_ordinal
_software.name
_software.classification
_software.description
_software.version
_software.type
_software.location
1 'test software' 'test class' 'test desc' program 1.0.1 https://example.org
""")
        s, = ihm.reader.read(fh)
        software, = s.software
        self.assertEqual(software._id, '1')
        self.assertEqual(software.name, 'test software')
        self.assertEqual(software.classification, 'test class')


    def test_citation_handler(self):
        """Test CitationHandler and CitationAuthorHandler"""
        fh = StringIO("""
loop_
_citation.id
_citation.journal_abbrev
_citation.journal_volume
_citation.page_first
_citation.page_last
_citation.year
2 'Mol Cell Proteomics' 9 2943 . 2014
3 'Mol Cell Proteomics' 9 2943 2946 2014
4 'Mol Cell Proteomics' 9 . . 2014
#
#
loop_
_citation_author.citation_id
_citation_author.name
_citation_author.ordinal
3 'Foo A' 1
3 'Bar C' 2
3 . 3
5 'Baz X' 4
""")
        s, = ihm.reader.read(fh)
        citation1, citation2, citation3, citation4 = s.citations
        self.assertEqual(citation1._id, '2')
        self.assertEqual(citation1.page_range, '2943')
        self.assertEqual(citation1.authors, [])

        self.assertEqual(citation2._id, '3')
        self.assertEqual(citation2.page_range, ('2943', '2946'))
        self.assertEqual(citation2.authors, ['Foo A', 'Bar C'])

        self.assertEqual(citation3._id, '4')
        self.assertEqual(citation3.authors, [])
        self.assertEqual(citation3.page_range, None)

        # todo: should probably be an error, no _citation.id == 4
        self.assertEqual(citation4._id, '5')
        self.assertEqual(citation4.authors, ['Baz X'])

    def test_chem_comp_handler(self):
        """Test ChemCompHandler and EntityPolySeqHandler"""
        fh = StringIO("""
loop_
_chem_comp.id
_chem_comp.type
MET 'L-peptide linking'
MYTYPE 'D-PEPTIDE LINKING'
#
#
loop_
_entity_poly_seq.entity_id
_entity_poly_seq.num
_entity_poly_seq.mon_id
_entity_poly_seq.hetero
1 1 MET .
1 4 MYTYPE .
1 2 MET .
""")
        s, = ihm.reader.read(fh)
        e1, = s.entities
        s = e1.sequence
        self.assertEqual(len(s), 4)
        lpeptide = ihm.LPeptideAlphabet()
        self.assertEqual(id(s[0]), id(lpeptide['M']))
        self.assertEqual(id(s[1]), id(lpeptide['M']))
        self.assertEqual(s[2], None)
        self.assertEqual(s[3].id, 'MYTYPE')
        self.assertEqual(s[3].type, 'D-peptide linking')
        self.assertEqual(s[3].__class__, ihm.DPeptideChemComp)

    def test_entity_handler(self):
        """Test EntityHandler"""
        fh = StringIO("""
loop_
_entity.id
_entity.type
_entity.pdbx_description
_entity.pdbx_number_of_molecules
_entity.details
1 polymer Nup84 2 .
2 polymer Nup85 3 .
""")
        s, = ihm.reader.read(fh)
        e1, e2 = s.entities
        self.assertEqual(e1.description, 'Nup84')
        self.assertEqual(e1.number_of_molecules, '2') # todo: coerce to int

    def test_asym_unit_handler(self):
        """Test AsymUnitHandler"""
        fh = StringIO("""
loop_
_struct_asym.id
_struct_asym.entity_id
_struct_asym.details
A 1 Nup84
B 1 Nup85
""")
        s, = ihm.reader.read(fh)
        a1, a2 = s.asym_units
        self.assertEqual(a1._id, 'A')
        self.assertEqual(a1.entity._id, '1')

        self.assertEqual(a1.details, 'Nup84')
        self.assertEqual(a2.entity._id, '1')
        self.assertEqual(a2._id, 'B')
        self.assertEqual(a2.details, 'Nup85')
        self.assertEqual(id(a1.entity), id(a2.entity))

    def test_assembly_details_handler(self):
        """Test AssemblyDetailsHandler"""
        fh = StringIO("""
loop_
_ihm_struct_assembly_details.assembly_id
_ihm_struct_assembly_details.assembly_name
_ihm_struct_assembly_details.assembly_description
1 'Complete assembly' 'All known components'
""")
        s, = ihm.reader.read(fh)
        a1, = s.orphan_assemblies
        self.assertEqual(a1._id, '1')
        self.assertEqual(a1.name, 'Complete assembly')
        self.assertEqual(a1.description, 'All known components')

    def test_assembly_handler(self):
        """Test AssemblyHandler"""
        fh = StringIO("""
loop_
_ihm_struct_assembly.ordinal_id
_ihm_struct_assembly.assembly_id
_ihm_struct_assembly.parent_assembly_id
_ihm_struct_assembly.entity_description
_ihm_struct_assembly.entity_id
_ihm_struct_assembly.asym_id
_ihm_struct_assembly.seq_id_begin
_ihm_struct_assembly.seq_id_end
1 1 1 Nup84 1 A 1 726
2 1 1 Nup85 2 B 1 744
3 2 1 Nup86 2 . 1 50
""")
        s, = ihm.reader.read(fh)
        a1, a2 = s.orphan_assemblies
        self.assertEqual(a1._id, '1')
        self.assertEqual(a1.parent, None)
        self.assertEqual(len(a1), 2)
        # AsymUnitRange
        self.assertEqual(a1[0]._id, 'A')
        self.assertEqual(a1[0].seq_id_range, (1,726))
        self.assertEqual(a1[1]._id, 'B')
        self.assertEqual(a1[1].seq_id_range, (1,744))

        self.assertEqual(a2._id, '2')
        self.assertEqual(a2.parent, a1)
        # EntityRange
        self.assertEqual(len(a2), 1)
        self.assertEqual(a2[0]._id, '2')
        self.assertEqual(a2[0].seq_id_range, (1,50))


if __name__ == '__main__':
    unittest.main()
