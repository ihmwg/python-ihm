import utils
import os
import unittest

TOPDIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
utils.set_search_paths(TOPDIR)
import ihm.dataset

def make_test_file(fname):
    with open(fname, 'w') as fh:
        fh.write('contents')

class Tests(unittest.TestCase):

    def test_pdb_location(self):
        """Test PDBLocation"""
        l = ihm.dataset.PDBLocation('1abc', version='foo', details='bar')
        self.assertEqual(l.db_name, 'PDB')
        self.assertEqual(l.access_code, '1abc')
        self.assertEqual(l.version, 'foo')
        self.assertEqual(l.details, 'bar')

    def test_emdb_location(self):
        """Test EMDBLocation"""
        l = ihm.dataset.EMDBLocation('EMDB-123', version='foo', details='bar')
        self.assertEqual(l.db_name, 'EMDB')
        self.assertEqual(l.access_code, 'EMDB-123')
        self.assertEqual(l.version, 'foo')
        self.assertEqual(l.details, 'bar')

    def test_duplicate_datasets_details(self):
        """Datasets with differing details should be considered duplicates"""
        with utils.temporary_directory() as tmpdir:
            fname = os.path.join(tmpdir, 'test.pdb')
            make_test_file(fname)
            l1 = ihm.dataset.FileLocation(fname, details='test details')
            d1 = ihm.dataset.PDBDataset(l1)

            l2 = ihm.dataset.FileLocation(fname, details='other details')
            d2 = ihm.dataset.PDBDataset(l2)
            self.assertEqual(l1, l2)

    def test_duplicate_locations(self):
        """Datasets with same location should be considered duplicates"""
        with utils.temporary_directory() as tmpdir:
            fname1 = os.path.join(tmpdir, 'test1.pdb')
            fname2 = os.path.join(tmpdir, 'test2.pdb')
            make_test_file(fname1)
            make_test_file(fname2)
            loc1 = ihm.dataset.FileLocation(fname1)
            loc2 = ihm.dataset.FileLocation(fname2)

            # Identical datasets in the same location aren't duplicated
            pdb1 = ihm.dataset.PDBDataset(loc1)
            pdb2 = ihm.dataset.PDBDataset(loc1)
            self.assertEqual(pdb1, pdb2)

            # Datasets in different locations are OK
            pdb1 = ihm.dataset.PDBDataset(loc1)
            pdb2 = ihm.dataset.PDBDataset(loc2)
            self.assertNotEqual(pdb1, pdb2)


if __name__ == '__main__':
    unittest.main()
