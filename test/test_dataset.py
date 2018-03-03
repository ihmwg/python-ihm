import utils
import os
import unittest

TOPDIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
utils.set_search_paths(TOPDIR)
import ihm.dataset

def _make_test_file(fname):
    with open(fname, 'w') as fh:
        fh.write('contents')

class Tests(unittest.TestCase):

    def test_dataset(self):
        """Test Dataset base class"""
        l = ihm.dataset.PDBLocation('1abc', version='foo', details='bar')
        d = ihm.dataset.Dataset(l)
        self.assertEqual(len(d._parents), 0)

        l2 = ihm.dataset.PDBLocation('1xyz', version='foo', details='bar')
        d2 = ihm.dataset.Dataset(l2)
        d.add_parent(d2)
        self.assertEqual(len(d._parents), 1)
        self.assertNotEqual(d, d2)
        # Ignore duplicates
        d.add_parent(d2)
        self.assertEqual(len(d._parents), 1)

    def test_experimental_datasets(self):
        """Exercise various experimental dataset classes"""
        l = ihm.dataset.PDBLocation('1abc', version='foo', details='bar')
        d = ihm.dataset.CXMSDataset(l)
        self.assertEqual(d.data_type, 'CX-MS data')

        d = ihm.dataset.PDBDataset(l)
        self.assertEqual(d.data_type, 'Experimental model')

        d = ihm.dataset.ComparativeModelDataset(l)
        self.assertEqual(d.data_type, 'Comparative model')

        d = ihm.dataset.EMDensityDataset(l)
        self.assertEqual(d.data_type, '3DEM volume')

    def test_database_location(self):
        """Test DatabaseLocation"""
        dl1 = ihm.dataset.DatabaseLocation('mydb', 'abc', version=1)
        dl2 = ihm.dataset.DatabaseLocation('mydb', 'abc', version=1)
        self.assertEqual(dl1, dl2)
        dl3 = ihm.dataset.DatabaseLocation('mydb', 'abc', version=2)
        self.assertNotEqual(dl1, dl3)
        # details can change without affecting equality
        dl4 = ihm.dataset.DatabaseLocation('mydb', 'abc', version=1,
                                                details='foo')
        self.assertEqual(dl1, dl4)
        self.assertEqual(dl1.db_name, 'mydb')
        self.assertEqual(dl1.access_code, 'abc')
        self.assertEqual(dl1.version, 1)
        self.assertEqual(dl1.details, None)

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
            _make_test_file(fname)
            l1 = ihm.dataset.InputFileLocation(fname, details='test details')
            d1 = ihm.dataset.PDBDataset(l1)

            l2 = ihm.dataset.InputFileLocation(fname, details='other details')
            d2 = ihm.dataset.PDBDataset(l2)
            self.assertEqual(l1, l2)

    def test_location(self):
        """Test Location base class"""
        l = ihm.dataset.Location(details='foo')
        l._allow_duplicates = True
        self.assertEqual(l._eq_vals(), id(l))

    def test_duplicate_locations(self):
        """Datasets with same location should be considered duplicates"""
        with utils.temporary_directory() as tmpdir:
            fname1 = os.path.join(tmpdir, 'test1.pdb')
            fname2 = os.path.join(tmpdir, 'test2.pdb')
            _make_test_file(fname1)
            _make_test_file(fname2)
            loc1 = ihm.dataset.InputFileLocation(fname1)
            loc2 = ihm.dataset.InputFileLocation(fname2)

            # Identical datasets in the same location aren't duplicated
            pdb1 = ihm.dataset.PDBDataset(loc1)
            pdb2 = ihm.dataset.PDBDataset(loc1)
            self.assertEqual(pdb1, pdb2)

            # Datasets in different locations are OK
            pdb1 = ihm.dataset.PDBDataset(loc1)
            pdb2 = ihm.dataset.PDBDataset(loc2)
            self.assertNotEqual(pdb1, pdb2)

    def test_file_location_local(self):
        """Test InputFileLocation with a local file"""
        with utils.temporary_directory() as tmpdir:
            fname = os.path.join(tmpdir, 'test.pdb')
            _make_test_file(fname)
            l = ihm.dataset.InputFileLocation(fname)
            self.assertEqual(l.path, os.path.abspath(fname))
            self.assertEqual(l.repo, None)
            self.assertEqual(l.file_size, 8)

    def test_file_location_local_not_exist(self):
        """Test InputFileLocation with a local file that doesn't exist"""
        with utils.temporary_directory() as tmpdir:
            fname = os.path.join(tmpdir, 'test.pdb')
            self.assertRaises(ValueError, ihm.dataset.InputFileLocation, fname)

    def test_file_location_repo(self):
        """Test InputFileLocation with a file in a repository"""
        r = ihm.dataset.Repository(doi='1.2.3.4')
        l = ihm.dataset.InputFileLocation('foo/bar', repo=r)
        self.assertEqual(l.path, 'foo/bar')
        self.assertEqual(l.repo, r)
        self.assertEqual(l.file_size, None)

    def test_repository_equality(self):
        """Test Repository equality"""
        r1 = ihm.dataset.Repository(doi='foo')
        r2 = ihm.dataset.Repository(doi='foo')
        r3 = ihm.dataset.Repository(doi='foo', url='bar')
        r4 = ihm.dataset.Repository(doi='bar')
        self.assertEqual(r1, r2)
        self.assertEqual(hash(r1), hash(r2))
        self.assertNotEqual(r1, r3)
        self.assertNotEqual(r1, r4)

    def test_repository(self):
        """Test Repository"""
        with utils.temporary_directory() as tmpdir:
            subdir = os.path.join(tmpdir, 'subdir')
            subdir2 = os.path.join(tmpdir, 'subdir2')
            os.mkdir(subdir)
            _make_test_file(os.path.join(subdir, 'bar'))
            s = ihm.dataset.Repository(doi='10.5281/zenodo.46266',
                                       root=tmpdir, url='foo',
                                       top_directory='baz')
            self.assertEqual(s._root, tmpdir)
            self.assertEqual(s.url, 'foo')
            self.assertEqual(s.top_directory, 'baz')

            loc = ihm.dataset.InputFileLocation(os.path.join(subdir, 'bar'))
            self.assertEqual(loc.repo, None)
            ihm.dataset.Repository._update_in_repos(loc, [s])
            self.assertEqual(loc.repo.doi, '10.5281/zenodo.46266')
            self.assertEqual(loc.path, os.path.join('subdir', 'bar'))

            # Shouldn't touch locations that are already in repos
            loc = ihm.dataset.InputFileLocation(repo='foo', path='bar')
            self.assertEqual(loc.repo, 'foo')
            ihm.dataset.Repository._update_in_repos(loc, [s])
            self.assertEqual(loc.repo, 'foo')

            # Shortest match should win
            loc = ihm.dataset.InputFileLocation((os.path.join(subdir, 'bar')))
            s2 = ihm.dataset.Repository(doi='10.5281/zenodo.46280', root=subdir,
                                        url='foo', top_directory='baz')
            # Repositories that aren't above the file shouldn't count
            s3 = ihm.dataset.Repository(doi='10.5281/zenodo.56280',
                                        root=subdir2, url='foo',
                                        top_directory='baz')
            ihm.dataset.Repository._update_in_repos(loc, [s2, s3, s])
            self.assertEqual(loc.repo.doi, '10.5281/zenodo.46280')
            self.assertEqual(loc.path, 'bar')

    def test_repository_no_checkout(self):
        """Test Repository with no checkout"""
        r = ihm.dataset.Repository(doi='10.5281/zenodo.46266')
        f = ihm.dataset.InputFileLocation(repo=r, path='foo')
        self.assertEqual(f.repo.doi, '10.5281/zenodo.46266')
        self.assertEqual(f.path, 'foo')

    def test_repository_get_full_path(self):
        """Test Repository._get_full_path"""
        r = ihm.dataset.Repository(doi='10.5281/zenodo.46266',
                                   top_directory='/foo')
        self.assertEqual(r._get_full_path('bar'), '/foo/bar')

    def test_file_locations(self):
        """Test FileLocation derived classes"""
        r = ihm.dataset.Repository(doi='10.5281/zenodo.46266')
        l = ihm.dataset.InputFileLocation(repo=r, path='foo')
        self.assertEqual(l.content_type, 'Input data or restraints')
        l = ihm.dataset.OutputFileLocation(repo=r, path='foo')
        self.assertEqual(l.content_type, 'Modeling or post-processing output')
        l = ihm.dataset.WorkflowFileLocation(repo=r, path='foo')
        self.assertEqual(l.content_type, 'Modeling workflow or script')
        l = ihm.dataset.VisualizationFileLocation(repo=r, path='foo')
        self.assertEqual(l.content_type, 'Visualization script')


if __name__ == '__main__':
    unittest.main()
