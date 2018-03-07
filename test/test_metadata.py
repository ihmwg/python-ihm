import utils
import os
import unittest
import sys
try:
    import urllib.request as urllib2
except ImportError:
    import urllib2
if sys.version_info[0] >= 3:
    from io import StringIO
else:
    from io import BytesIO as StringIO

TOPDIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
utils.set_search_paths(TOPDIR)
import ihm.metadata

class Tests(unittest.TestCase):

    def test_mrc_parser_local_mrc(self):
        """Test MRCParser pointing to a locally-available MRC file"""
        p = ihm.metadata.MRCParser()
        # Note that this is not a complete MRC file (only the header),
        # to save space in the repository
        fname = utils.get_input_file_name(TOPDIR, 'Rpb8.mrc-header')
        d = p.parse_file(fname)
        self.assertEqual(list(d.keys()), ['dataset'])
        dataset = d['dataset']
        self.assertEqual(dataset.data_type, '3DEM volume')
        self.assertEqual(dataset.location.path, fname)
        self.assertEqual(dataset.location.details,
                         'Electron microscopy density map')
        self.assertEqual(dataset.location.repo, None)

    def test_mrc_parser_emdb(self):
        """Test MRCParser pointing to an MRC in EMDB"""
        def mock_urlopen(url):
            txt = '{"EMD-1883":[{"deposition":{"map_release_date":"2011-04-21"'\
                  ',"title":"test details"}}]}'
            return StringIO(txt)
        p = ihm.metadata.MRCParser()
        fname = utils.get_input_file_name(TOPDIR, 'emd_1883.map.mrc-header')

        # Need to mock out urllib2 so we don't hit the network (expensive)
        # every time we test
        try:
            orig_urlopen = urllib2.urlopen
            urllib2.urlopen = mock_urlopen
            d = p.parse_file(fname)
        finally:
            urllib2.urlopen = orig_urlopen
        self.assertEqual(list(d.keys()), ['dataset'])
        dataset = d['dataset']
        self.assertEqual(dataset.data_type, '3DEM volume')
        self.assertEqual(dataset.location.db_name, 'EMDB')
        self.assertEqual(dataset.location.access_code, 'EMD-1883')
        self.assertEqual(dataset.location.version, '2011-04-21')
        self.assertEqual(dataset.location.details, 'test details')


if __name__ == '__main__':
    unittest.main()
