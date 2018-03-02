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

    def test_entry_dumper(self):
        """Test EntryDumper"""
        system = ihm.System(name='test_model')
        dumper = ihm.dumper._EntryDumper()
        out = _get_dumper_output(dumper, system)
        self.assertEqual(out, "data_test_model\n_entry.id test_model\n")


if __name__ == '__main__':
    unittest.main()
