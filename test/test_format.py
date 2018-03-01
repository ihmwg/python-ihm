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
import ihm.format

class StringWriter(object):
    def __init__(self):
        self.fh = StringIO()
    def _repr(self, val):
        return repr(val)
    def getvalue(self):
        return self.fh.getvalue()


class Tests(unittest.TestCase):
    def test_line_writer_wrap(self):
        """Test LineWriter class line wrap"""
        writer = StringWriter()
        lw = ihm.format._LineWriter(writer, line_len=15)
        lw.write("foo")
        self.assertEqual(writer.getvalue(), "'foo'")
        lw.write("bar")
        self.assertEqual(writer.getvalue(), "'foo' 'bar'")
        lw.write("baz")
        self.assertEqual(writer.getvalue(), "'foo' 'bar'\n'baz'")

    def test_line_writer_multiline(self):
        """Test LineWriter class given a multiline string"""
        writer = StringWriter()
        lw = ihm.format._LineWriter(writer, line_len=15)
        lw.write("foo\nbar\nbaz")
        self.assertEqual(writer.getvalue(), "\n;foo\nbar\nbaz\n;\n")

if __name__ == '__main__':
    unittest.main()
