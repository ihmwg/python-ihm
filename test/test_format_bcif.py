import utils
import os
import unittest
import sys

TOPDIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
utils.set_search_paths(TOPDIR)
import ihm.format_bcif

class Tests(unittest.TestCase):
    def test_decoder_base(self):
        """Test Decoder base class"""
        d = ihm.format_bcif._Decoder()
        self.assertEqual(d._kind, None)
        d(enc=None, data=None) # noop

    def test_string_array_decoder(self):
        """Test StringArray decoder"""
        d = ihm.format_bcif._StringArrayDecoder()
        self.assertEqual(d._kind, b'StringArray')

        # type 1 is signed char (so FF is -1)
        enc = {b'stringData': b'aAB',
               b'dataEncoding': [{b'kind':b'ByteArray', b'type':1}],
               b'offsetEncoding': [{b'kind':b'ByteArray', b'type':1}],
               b'offsets':b'\x00\x01\x03'}
        data = b'\x00\x01\x00\xFF'

        data = d(enc, data)
        self.assertEqual(list(data), [b'a', b'AB', b'a', None])

    def test_byte_array_decoder(self):
        """Test ByteArray decoder"""
        d = ihm.format_bcif._ByteArrayDecoder()
        self.assertEqual(d._kind, b'ByteArray')

        # type 1 (signed char)
        data = d({b'type':1}, b'\x00\x01\xFF')
        self.assertEqual(list(data), [0, 1, -1])

        # type 2 (signed short)
        data = d({b'type':2}, b'\x00\x01\x01\xAC')
        self.assertEqual(list(data), [256, -21503])

        # type 3 (signed int)
        data = d({b'type':3}, b'\x00\x01\x01\x05')
        self.assertEqual(list(data), [83951872])

        # type 4 (unsigned char)
        data = d({b'type':4}, b'\x00\xFF')
        self.assertEqual(list(data), [0, 255])

        # type 5 (unsigned short)
        data = d({b'type':5}, b'\x00\x01\x01\xAC')
        self.assertEqual(list(data), [256, 44033])

        # type 6 (unsigned int)
        data = d({b'type':6}, b'\x00\x01\x01\xFF')
        self.assertEqual(list(data), [4278255872])

        # type 32 (32-bit float)
        data = d({b'type':32}, b'\x00\x00(B')
        self.assertAlmostEqual(list(data)[0], 42.0, places=1)

        # type 33 (64-bit float)
        data = d({b'type':33}, b'\x00\x00\x00\x00\x00\x00E@')
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
        bytearr = {b'kind': b'ByteArray', b'type':1}
        data = ihm.format_bcif._decode(data, [runlen, bytearr])
        self.assertEqual(list(data), [1, 1, 1, 2, 3, 3])


if __name__ == '__main__':
    unittest.main()
