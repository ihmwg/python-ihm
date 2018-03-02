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
import ihm.dumper
import ihm.format

def _get_dumper_output(dumper, system):
    fh = StringIO()
    writer = ihm.format.CifWriter(fh)
    dumper.dump(system, writer)
    return fh.getvalue()

class Tests(unittest.TestCase):
    def test_write(self):
        """Test write() function"""
        sys1 = ihm.System('system1')
        sys2 = ihm.System('system 2+3')
        fh = StringIO()
        ihm.dumper.write(fh, [sys1, sys2])
        self.assertEqual(fh.getvalue(), """data_system1
_entry.id system1
data_system23
_entry.id 'system 2+3'
""")

    def test_dumper(self):
        """Test Dumper base class"""
        dumper = ihm.dumper._Dumper()
        dumper.finalize(None)
        dumper.dump(None, None)

    def test_entry_dumper(self):
        """Test EntryDumper"""
        system = ihm.System(name='test_model')
        dumper = ihm.dumper._EntryDumper()
        out = _get_dumper_output(dumper, system)
        self.assertEqual(out, "data_test_model\n_entry.id test_model\n")

    def test_software(self):
        """Test SoftwareDumper"""
        system = ihm.System()
        system.software.append(ihm.Software(
                         name='test', classification='test code',
                         description='Some test program',
                         version=1, location='http://test.org'))
        system.software.append(ihm.Software(
                          name='foo', classification='test code',
                          description='Other test program',
                          location='http://test2.org'))
        dumper = ihm.dumper._SoftwareDumper()
        out = _get_dumper_output(dumper, system)
        self.assertEqual(out, """#
loop_
_software.pdbx_ordinal
_software.name
_software.classification
_software.description
_software.version
_software.type
_software.location
1 test 'test code' 'Some test program' 1 program http://test.org
2 foo 'test code' 'Other test program' . program http://test2.org
#
""")

    def test_entity_dumper(self):
        """Test EntityDumper"""
        system = ihm.System()
        system.entities.append(ihm.Entity('ABC', description='foo'))
        system.entities.append(ihm.Entity('ABCD', description='baz'))
        dumper = ihm.dumper._EntityDumper()
        dumper.finalize(system) # Assign IDs
        out = _get_dumper_output(dumper, system)
        self.assertEqual(out, """#
loop_
_entity.id
_entity.type
_entity.src_method
_entity.pdbx_description
_entity.formula_weight
_entity.pdbx_number_of_molecules
_entity.details
1 polymer man foo ? 1 .
2 polymer man baz ? 1 .
#
""")

    def test_entity_duplicates(self):
        """Test EntityDumper with duplicate entities"""
        system = ihm.System()
        system.entities.append(ihm.Entity('ABC'))
        system.entities.append(ihm.Entity('ABC'))
        dumper = ihm.dumper._EntityDumper()
        self.assertRaises(ValueError, dumper.finalize, system)

    def test_chem_comp_dumper(self):
        """Test ChemCompDumper"""
        system = ihm.System()
        system.entities.append(ihm.Entity('ACGTTA'))
        dumper = ihm.dumper._ChemCompDumper()
        out = _get_dumper_output(dumper, system)
        self.assertEqual(out, """#
loop_
_chem_comp.id
_chem_comp.type
ALA 'L-peptide linking'
CYS 'L-peptide linking'
GLY 'L-peptide linking'
THR 'L-peptide linking'
#
""")

    def test_entity_poly_dumper(self):
        """Test EntityPolyDumper"""
        system = ihm.System()
        e1 = ihm.Entity('ACGT')
        e2 = ihm.Entity('ACC')
        system.entities.extend((e1, e2))
        # One entity is modeled (with an asym unit) the other not; this should
        # be reflected in pdbx_strand_id
        system.asym_units.append(ihm.AsymUnit(e1, 'foo'))
        ed = ihm.dumper._EntityDumper()
        ed.finalize(system) # Assign entity IDs
        sd = ihm.dumper._StructAsymDumper()
        sd.finalize(system) # Assign asym IDs
        dumper = ihm.dumper._EntityPolyDumper()
        out = _get_dumper_output(dumper, system)
        self.assertEqual(out, """#
loop_
_entity_poly.entity_id
_entity_poly.type
_entity_poly.nstd_linkage
_entity_poly.nstd_monomer
_entity_poly.pdbx_strand_id
_entity_poly.pdbx_seq_one_letter_code
_entity_poly.pdbx_seq_one_letter_code_can
1 polypeptide(L) no no A ACGT ACGT
2 polypeptide(L) no no . ACC ACC
#
""")

    def test_entity_poly_seq_dumper(self):
        """Test EntityPolySeqDumper"""
        system = ihm.System()
        system.entities.append(ihm.Entity('ACGT'))
        system.entities.append(ihm.Entity('ACC'))
        ed = ihm.dumper._EntityDumper()
        ed.finalize(system) # Assign IDs
        dumper = ihm.dumper._EntityPolySeqDumper()
        out = _get_dumper_output(dumper, system)
        self.assertEqual(out, """#
loop_
_entity_poly_seq.entity_id
_entity_poly_seq.num
_entity_poly_seq.mon_id
_entity_poly_seq.hetero
1 1 ALA .
1 2 CYS .
1 3 GLY .
1 4 THR .
2 1 ALA .
2 2 CYS .
2 3 CYS .
#
""")

    def test_struct_asym_dumper(self):
        """Test StructAsymDumper"""
        system = ihm.System()
        e1 = ihm.Entity('ACGT')
        e2 = ihm.Entity('ACC')
        e1.id = 1
        e2.id = 2
        system.entities.extend((e1, e2))
        system.asym_units.append(ihm.AsymUnit(e1, 'foo'))
        system.asym_units.append(ihm.AsymUnit(e1, 'bar'))
        system.asym_units.append(ihm.AsymUnit(e2, 'baz'))
        dumper = ihm.dumper._StructAsymDumper()
        dumper.finalize(system) # assign IDs
        out = _get_dumper_output(dumper, system)
        self.assertEqual(out, """#
loop_
_struct_asym.id
_struct_asym.entity_id
_struct_asym.details
A 1 foo
B 1 bar
C 2 baz
#
""")


if __name__ == '__main__':
    unittest.main()
