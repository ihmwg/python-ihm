import utils
import os
import unittest
import sys

TOPDIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
utils.set_search_paths(TOPDIR)
import ihm.format_bcif

# Provide a dummy implementation of msgpack.unpack() which just returns the
# data unchanged. We can use this to test the BinaryCIF parser with Python
# objects rather than having to install msgpack and generate real binary files
class MockMsgPack(object):
    @staticmethod
    def unpack(fh):
        return fh

class GenericHandler(object):
    """Capture BinaryCIF data as a simple list of dicts"""

    _keys = ('method', 'foo', 'bar', 'baz', 'pdbx_keywords', 'var1',
             'var2', 'var3')

    def __init__(self):
        self.data = []

    def __call__(self, *args):
        d = {}
        for k, v in zip(self._keys, args):
            if v is not None:
                d[k] = v
        self.data.append(d)


def _encode(rows):
    # Assume rows is a list of strings; make simple BinaryCIF encoding
    mask = [0] * len(rows)
    need_mask = False
    for i, row in enumerate(rows):
        if row is None:
            need_mask = True
            mask[i] = 1
        elif row == '?':
            need_mask = True
            mask[i] = 2
    if need_mask:
        rows = ['' if r == '?' or r is None else r for r in rows]
        mask_data = ''.join(chr(i) for i in mask).encode('ascii')
        mask = {b'data': ''.join(chr(i) for i in mask).encode('ascii'),
                b'encoding': [{b'kind': b'ByteArray',
                               b'type': ihm.format_bcif._Uint8}]}
    else:
        mask = None
    string_data = "".join(rows)

    offsets = []
    total_len = 0
    for row in rows:
        offsets.append(total_len)
        total_len += len(row)
    offsets.append(total_len)
    offsets = ''.join(chr(i) for i in offsets).encode('ascii')
    indices = ''.join(chr(i) for i in range(len(rows))).encode('ascii')
    string_array_encoding = {
         b'kind': b'StringArray',
         b'dataEncoding': [{b'kind': b'ByteArray',
                            b'type': ihm.format_bcif._Uint8}],
         b'stringData': string_data.encode('ascii'),
         b'offsetEncoding': [{b'kind': b'ByteArray',
                              b'type': ihm.format_bcif._Uint8}],
         b'offsets': offsets }
    d = {b'data': indices,
         b'encoding': [string_array_encoding]}
    return d, mask

class Category(object):
    def __init__(self, name, data):
        self.name = name
        self.data = data

    def get_bcif(self):
        nrows = 0
        cols = []
        for name, rows in self.data.items():
            nrows = len(rows)
            data, mask = _encode(rows)
            cols.append({b'mask': mask, b'name': name.encode('ascii'),
                         b'data': data})
        return {b'name': self.name.encode('ascii'),
                b'columns': cols, b'rowCount': nrows}


class Block(list):
    pass


def _make_bcif_file(blocks):
    blocks = [{b'header':'ihm',
               b'categories':[c.get_bcif() for c in block]}
              for block in blocks]
    return {b'version':'0.1', b'encoder':'python-ihm test suite',
            b'dataBlocks':blocks}

class Tests(unittest.TestCase):
    def test_decode_bytes(self):
        """Test decode_bytes function"""
        d = ihm.format_bcif._decode_bytes(b'foo')
        self.assertEqual(d, 'foo')

    def test_decoder_base(self):
        """Test Decoder base class"""
        d = ihm.format_bcif._Decoder()
        self.assertEqual(d._kind, None)
        d(enc=None, data=None) # noop

    def test_string_array_decoder(self):
        """Test StringArray decoder"""
        d = ihm.format_bcif._StringArrayDecoder()
        self.assertEqual(d._kind, b'StringArray')

        # Int8 is signed char (so FF is -1)
        enc = {b'stringData': b'aAB',
               b'dataEncoding': [{b'kind':b'ByteArray',
                                  b'type':ihm.format_bcif._Int8}],
               b'offsetEncoding': [{b'kind':b'ByteArray',
                                    b'type':ihm.format_bcif._Int8}],
               b'offsets':b'\x00\x01\x03'}
        data = b'\x00\x01\x00\xFF'

        data = d(enc, data)
        self.assertEqual(list(data), ['a', 'AB', 'a', None])

    def test_byte_array_decoder(self):
        """Test ByteArray decoder"""
        d = ihm.format_bcif._ByteArrayDecoder()
        self.assertEqual(d._kind, b'ByteArray')

        # type 1 (signed char)
        data = d({b'type':ihm.format_bcif._Int8}, b'\x00\x01\xFF')
        self.assertEqual(list(data), [0, 1, -1])

        # type 2 (signed short)
        data = d({b'type':ihm.format_bcif._Int16}, b'\x00\x01\x01\xAC')
        self.assertEqual(list(data), [256, -21503])

        # type 3 (signed int)
        data = d({b'type':ihm.format_bcif._Int32}, b'\x00\x01\x01\x05')
        self.assertEqual(list(data), [83951872])

        # type 4 (unsigned char)
        data = d({b'type':ihm.format_bcif._Uint8}, b'\x00\xFF')
        self.assertEqual(list(data), [0, 255])

        # type 5 (unsigned short)
        data = d({b'type':ihm.format_bcif._Uint16}, b'\x00\x01\x01\xAC')
        self.assertEqual(list(data), [256, 44033])

        # type 6 (unsigned int)
        data = d({b'type':ihm.format_bcif._Uint32}, b'\x00\x01\x01\xFF')
        self.assertEqual(list(data), [4278255872])

        # type 32 (32-bit float)
        data = d({b'type':ihm.format_bcif._Float32}, b'\x00\x00(B')
        self.assertAlmostEqual(list(data)[0], 42.0, places=1)

        # type 33 (64-bit float)
        data = d({b'type':ihm.format_bcif._Float64},
                  b'\x00\x00\x00\x00\x00\x00E@')
        self.assertAlmostEqual(list(data)[0], 42.0, places=1)

    def test_integer_packing_decoder_signed(self):
        """Test IntegerPacking decoder with signed data"""
        d = ihm.format_bcif._IntegerPackingDecoder()
        self.assertEqual(d._kind, b'IntegerPacking')

        # 1-byte data
        data = d({b'isUnsigned':False, b'byteCount':1},
                 [1, 2, -3, 127, 1, -128, -5])
        self.assertEqual(list(data), [1, 2, -3, 128, -133])

        # 2-byte data
        data = d({b'isUnsigned':False, b'byteCount':2},
                 [1, 2, -3, 32767, 1, -32768, -5])
        self.assertEqual(list(data), [1, 2, -3, 32768, -32773])

    def test_integer_packing_decoder_unsigned(self):
        """Test IntegerPacking decoder with unsigned data"""
        d = ihm.format_bcif._IntegerPackingDecoder()
        self.assertEqual(d._kind, b'IntegerPacking')

        # 1-byte data
        data = d({b'isUnsigned':True, b'byteCount':1},
                 [1, 2, 3, 127, 1, 255, 1])
        self.assertEqual(list(data), [1, 2, 3, 127, 1, 256])

        # 2-byte data
        data = d({b'isUnsigned':True, b'byteCount':2},
                 [1, 2, 3, 32767, 1, 65535, 5])
        self.assertEqual(list(data), [1, 2, 3, 32767, 1, 65540])

    def test_delta_decoder(self):
        """Test Delta decoder"""
        d = ihm.format_bcif._DeltaDecoder()
        self.assertEqual(d._kind, b'Delta')

        data = d({b'origin':1000}, [0, 3, 2, 1])
        self.assertEqual(list(data), [1000, 1003, 1005, 1006])

    def test_run_length_decoder(self):
        """Test RunLength decoder"""
        d = ihm.format_bcif._RunLengthDecoder()
        self.assertEqual(d._kind, b'RunLength')

        data = d({}, [1, 3, 2, 1, 3, 2])
        self.assertEqual(list(data), [1, 1, 1, 2, 3, 3])

    def test_fixed_point_decoder(self):
        """Test FixedPoint decoder"""
        d = ihm.format_bcif._FixedPointDecoder()
        self.assertEqual(d._kind, b'FixedPoint')

        data = list(d({b'factor':100}, [120, 123, 12]))
        self.assertEqual(len(data), 3)
        self.assertAlmostEqual(data[0], 1.20, places=2)
        self.assertAlmostEqual(data[1], 1.23, places=2)
        self.assertAlmostEqual(data[2], 0.12, places=2)

    def test_decode(self):
        """Test _decode function"""
        data = b'\x01\x03\x02\x01\x03\x02'
        runlen = {b'kind': b'RunLength'}
        bytearr = {b'kind': b'ByteArray', b'type':ihm.format_bcif._Int8}
        data = ihm.format_bcif._decode(data, [runlen, bytearr])
        self.assertEqual(list(data), [1, 1, 1, 2, 3, 3])

    def _read_bcif(self, blocks, category_handlers):
        fh = _make_bcif_file(blocks)
        sys.modules['msgpack'] = MockMsgPack
        r = ihm.format_bcif.BinaryCifReader(fh, category_handlers)
        r.read_file()

    def test_category_case_insensitive(self):
        """Categories and keywords should be case insensitive"""
        cat1 = Category('_exptl', {'method':['foo']})
        cat2 = Category('_Exptl', {'METHod':['foo']})
        for cat in cat1, cat2:
            h = GenericHandler()
            self._read_bcif([Block([cat])], {'_exptl':h})
        self.assertEqual(h.data, [{'method':'foo'}])

    def test_omitted_missing(self):
        """Test handling of omitted/missing data"""
        cat = Category('_foo', {'var1':['test1', '?', 'test2', None, 'test3']})
        h = GenericHandler()
        self._read_bcif([Block([cat])], {'_foo':h})
        self.assertEqual(h.data,
                         [{'var1': 'test1'}, {'var1': '?'}, {'var1': 'test2'},
                          {}, {'var1': 'test3'}])

    def test_extra_categories_ignored(self):
        """Check that extra categories in the file are ignored"""
        cat1 = Category('_foo', {'var1':['test1']})
        cat2 = Category('_bar', {'var2':['test2']})
        h = GenericHandler()
        self._read_bcif([Block([cat1, cat2])], {'_foo':h})
        self.assertEqual(h.data, [{'var1': 'test1'}])

    def test_extra_keywords_ignored(self):
        """Check that extra keywords in the file are ignored"""
        cat = Category('_foo', {'var1':['test1'], 'othervar':['test2']})
        h = GenericHandler()
        self._read_bcif([Block([cat])], {'_foo':h})
        self.assertEqual(h.data, [{'var1': 'test1'}])

    def test_multiple_data_blocks(self):
        """Test handling of multiple data blocks"""
        block1 = Block([Category('_foo', {'var1':['test1'], 'var2':['test2']})])
        block2 = Block([Category('_foo', {'var3':['test3']})])
        fh = _make_bcif_file([block1, block2])

        h = GenericHandler()
        r = ihm.format_bcif.BinaryCifReader(fh, {'_foo':h})
        sys.modules['msgpack'] = MockMsgPack
        # Read first data block
        self.assertTrue(r.read_file())
        self.assertEqual(h.data, [{'var1':'test1', 'var2':'test2'}])

        # Read second data block
        h.data = []
        self.assertFalse(r.read_file())
        self.assertEqual(h.data, [{'var3':'test3'}])

        # No more data blocks
        h.data = []
        self.assertFalse(r.read_file())
        self.assertEqual(h.data, [])


if __name__ == '__main__':
    unittest.main()
