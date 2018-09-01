"""Utility classes to handle BinaryCIF format.

   See https://github.com/dsehnal/BinaryCIF for a description of the
   BinaryCIF file format.

   This module provides classes to read in BinaryCIF files. It is
   only concerned with handling syntactically correct BinaryCIF -
   it does not know the set of tables or the mapping to ihm objects. For that,
   see :mod:`ihm.reader`. No write support currently exists.
"""

from __future__ import division
import struct
import sys
import inspect
import ihm.format

# ByteArray types
_Int8 = 1
_Int16 = 2
_Int32 = 3
_Uint8 = 4
_Uint16 = 5
_Uint32 = 6
_Float32 = 32
_Float64 = 33

# msgpack data is binary (bytes); need to convert to str in Python 3
# All mmCIF data is ASCII
if sys.version_info[0] >= 3:
    def _decode_bytes(bs):
        return bs.decode('ascii')
else:
    def _decode_bytes(bs):
        return bs

class _Decoder(object):
    """Base class for all decoders."""

    _kind = None # Encoder kind (in BinaryCIF specification)

    def __call__(self, enc, data):
        """Given encoding information `enc` and raw data `data`, return
           decoded data. This can be a generator."""
        pass


class _StringArrayDecoder(_Decoder):
    """Decode an array of strings stored as a concatenation of all unique
       strings, an array of offsets describing substrings, and indices into
       the offset array."""
    _kind = b'StringArray'

    def __call__(self, enc, data):
        offsets = list(_decode(enc[b'offsets'], enc[b'offsetEncoding']))
        indices = _decode(data, enc[b'dataEncoding'])
        substr = []
        string_data = _decode_bytes(enc[b'stringData'])
        for i in range(0, len(offsets) - 1):
            substr.append(string_data[offsets[i]:offsets[i+1]])
        # todo: return a listlike class instead?
        for i in indices:
            yield None if i < 0 else substr[i]


class _ByteArrayDecoder(_Decoder):
    """Decode an array of numbers of specified type stored as raw bytes"""

    _kind = b'ByteArray'

    # Map integer/float type to struct format string
    _struct_map = {
        _Int8: 'b',
        _Int16: 'h',
        _Int32: 'i',
        _Uint8: 'B',
        _Uint16: 'H',
        _Uint32: 'I',
        _Float32: 'f',
        _Float64: 'd',
    }

    def __call__(self, enc, data):
        fmt = self._struct_map[enc[b'type']]
        sz = len(data) // struct.calcsize(fmt)
        # All data is encoded little-endian in bcif
        return struct.unpack('<' + fmt * sz, data)


class _IntegerPackingDecoder(_Decoder):
    """Decode a (32-bit) integer array stored as 8- or 16-bit values."""
    _kind = b'IntegerPacking'

    def _unsigned_decode(self, enc, data):
        limit = 0xFF if enc[b'byteCount'] == 1 else 0xFFFF
        i = 0
        while i < len(data):
            value = 0
            t = data[i]
            while t == limit:
                value += t
                i += 1
                t = data[i]
            yield value + t
            i += 1

    def _signed_decode(self, enc, data):
        upper_limit = 0x7F if enc[b'byteCount'] == 1 else 0x7FFF
        lower_limit = -upper_limit - 1
        i = 0
        while i < len(data):
            value = 0
            t = data[i]
            while t == upper_limit or t == lower_limit:
                value += t
                i += 1
                t = data[i]
            yield value + t
            i += 1

    def __call__(self, enc, data):
        if enc[b'isUnsigned']:
            return self._unsigned_decode(enc, data)
        else:
            return self._signed_decode(enc, data)


class _DeltaDecoder(_Decoder):
    """Decode an integer array stored as an array of consecutive differences."""
    _kind = b'Delta'

    def __call__(self, enc, data):
        val = enc[b'origin']
        for d in data:
            val += d
            yield val


class _RunLengthDecoder(_Decoder):
    """Decode an integer array stored as pairs of (value, number of repeats)"""
    _kind = b'RunLength'

    def __call__(self, enc, data):
        data = list(data)
        for i in range(0, len(data), 2):
            for j in range(data[i+1]):
                yield data[i]


class _FixedPointDecoder(_Decoder):
    """Decode a floating point array stored as integers multiplied by
       a given factor."""
    _kind = b'FixedPoint'

    def __call__(self, enc, data):
        factor = float(enc[b'factor'])
        for d in data:
            yield float(d) / factor

def _get_decoder_map():
    m = {}
    for d in [x[1] for x in inspect.getmembers(sys.modules[__name__],
                                inspect.isclass) if issubclass(x[1], _Decoder)]:
        m[d._kind] = d()
    return m

# Mapping from BinaryCIF encoding names to _Decoder objects
_decoder_map = _get_decoder_map()

def _decode(data, encoding):
    """Decode the data using the list of encodings, and return it."""
    for enc in reversed(encoding):
        data = _decoder_map[enc[b'kind']](enc, data)
    return data


class BinaryCifReader(ihm.format._Reader):
    """Class to read an mmCIF file and extract some or all of its data.

       Use :meth:`read_file` to actually read the file.
       See :class:`ihm.format.CifReader` for a description of the parameters.
    """
    def __init__(self, fh, category_handler):
        self.category_handler = category_handler
        self.fh = fh
        self._file_blocks = None

    def read_file(self):
        """Read the file and extract data.
           :return: True iff more data blocks are available to be read.
        """
        self._add_category_keys()
        if self._file_blocks is None:
            self._file_blocks = self._read_msgpack()
        if len(self._file_blocks) > 0:
            for category in self._file_blocks[0][b'categories']:
                cat_name = _decode_bytes(category[b'name']).lower()
                handler = self.category_handler.get(cat_name, None)
                if handler:
                    self._handle_category(handler, category)
            del self._file_blocks[0]
        return len(self._file_blocks) > 0

    def _handle_category(self, handler, category):
        """Extract data for the given category"""
        num_cols = len(handler._keys)
        # Read all data for the category;
        # category_data[col][row]
        category_data = [None] * num_cols
        num_rows = 0
        # Only read columns that match a handler key (case insensitive)
        key_index = {}
        for i, key in enumerate(handler._keys):
            key_index[key] = i
        column_indices = []
        for c in category[b'columns']:
            ki = key_index.get(_decode_bytes(c[b'name']).lower(), None)
            if ki is not None:
                column_indices.append(ki)
                r = self._read_column(c)
                num_rows = len(r)
                category_data[ki] = r
        row_data = [None] * num_cols
        for row in range(num_rows):
            # Only update data for columns that we read (others will
            # remain None)
            for i in column_indices:
                row_data[i] = category_data[i][row]
            handler(*row_data)

    def _read_column(self, column):
        """Read a single category column data"""
        data = _decode(column[b'data'][b'data'], column[b'data'][b'encoding'])
        # Handle 'unknown' values (mask==2) or 'omitted' (mask==1)
        if column[b'mask'] is not None:
            mask = _decode(column[b'mask'][b'data'],
                           column[b'mask'][b'encoding'])
            data = ['?' if m == 2 else None if m == 1 else d
                    for d, m in zip(data, mask)]
        return list(data)

    def _read_msgpack(self):
        """Read the msgpack data from the file and return data blocks"""
        import msgpack
        d = msgpack.unpack(self.fh)
        return d[b'dataBlocks']
