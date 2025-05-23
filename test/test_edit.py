import utils
import os
import unittest
from io import StringIO

TOPDIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
utils.set_search_paths(TOPDIR)
import ihm.reader
import ihm.dumper


class Tests(unittest.TestCase):
    def test_entity(self):
        """Test Entity read followed by write"""
        sin = StringIO("""
loop_
_entity.id
_entity.type
_entity.pdbx_description
_entity.pdbx_number_of_molecules
_entity.formula_weight
_entity.details
1 polymer Nup84 2 100.0 .
#
loop_
_entity_poly_seq.entity_id
_entity_poly_seq.num
_entity_poly_seq.mon_id
_entity_poly_seq.hetero
1 1 ALA .
1 2 CYS .
""")
        s, = ihm.reader.read(sin)
        sout = StringIO()
        ihm.dumper.write(sout, [s])

    def test_orphan(self):
        """Make sure orphaned objects are preserved"""
        incif = utils.get_input_file_name(TOPDIR, 'orphan.cif')
        with open(incif) as fh:
            s, = ihm.reader.read(fh)
        sout = StringIO()
        ihm.dumper.write(sout, [s])
        newcif = sout.getvalue()
        # Make sure orphan object tables show up in the output
        self.assertIn('_ihm_geometric_object_center', newcif)
        self.assertIn('_ihm_relaxation_time', newcif)
        self.assertIn('_ihm_external_reference_info', newcif)
        self.assertIn('_chem_comp.', newcif)


if __name__ == '__main__':
    unittest.main()
