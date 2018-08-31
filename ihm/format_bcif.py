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
        for i in range(0, len(offsets) - 1):
            substr.append(enc[b'stringData'][offsets[i]:offsets[i+1]])
        # todo: return a listlike class instead?
        for i in indices:
            yield None if i < 0 else substr[i]


class _ByteArrayDecoder(_Decoder):
    """Decode an array of numbers of specified type stored as raw bytes"""

    _kind = b'ByteArray'

    # Map integer/float type to struct format string
    _struct_map = {
        1: 'b',  # Int8
        2: 'h',  # Int16
        3: 'i',  # Int32
        4: 'B',  # Uint8
        5: 'H',  # Uint16
        6: 'I',  # Uint32
        32: 'f', # Float32
        33: 'd', # Float64
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
