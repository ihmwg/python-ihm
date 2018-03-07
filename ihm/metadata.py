"""Classes to extract metadata from various input files.

   Often input files contain metadata that would be useful to include in
   the mmCIF file, but the metadata is stored in a different way for each
   domain-specific file type. For example, MRC files used for electron
   microscopy maps may contain an EMDB identifier, which the mmCIF file
   can point to in preference to the local file.

   This module provides classes for each file type to extract suitable
   metadata where available.
"""

from . import location, dataset

import struct
import json
import sys
import re

# Handle different naming of urllib in Python 2/3
try:
    import urllib.request as urllib2
except ImportError:
    import urllib2

class Parser(object):
    """Base class for all metadata parsers."""

    def parse_file(self, filename):
        """Extract metadata from the given file.

           :param str filename: the file to extract metadata from.
           :return: a dict with extracted metadata (generally including
                    a :class:`dataset.Dataset`)."""
        pass


class MRCParser(Parser):
    """Extract metadata from an EM density map (MRC file)."""

    def parse_file(self, filename):
        """Extract metadata. See :meth:`Parser.parse_file` for details.

           :return: a dict with key `dataset` pointing to the density map,
                    as an EMDB entry if the file contains EMDB headers,
                    otherwise to the file itself.
        """
        emdb = self._get_emdb(filename)
        if emdb:
            version, details = self._get_emdb_info(emdb)
            l = location.EMDBLocation(emdb, version=version,
                                      details=details if details
                                         else "Electron microscopy density map")
        else:
            l = location.InputFileLocation(filename,
                                      details="Electron microscopy density map")
        return {'dataset': dataset.EMDensityDataset(l)}

    def _get_emdb_info(self, emdb):
        """Query EMDB API and return version & details of a given entry"""
        req = urllib2.Request('https://www.ebi.ac.uk/pdbe/api/emdb/entry/'
                              'summary/%s' % emdb, None, {})
        response = urllib2.urlopen(req)
        contents = json.load(response)
        keys = list(contents.keys())
        info = contents[keys[0]][0]['deposition']
        # JSON values are always Unicode, but on Python 2 we want non-Unicode
        # strings, so convert to ASCII
        if sys.version_info[0] < 3:
            return (info['map_release_date'].encode('ascii'),
                    info['title'].encode('ascii'))
        else:
            return info['map_release_date'], info['title']

    def _get_emdb(self, filename):
        """Return the EMDB id of the file, or None."""
        r = re.compile(b'EMDATABANK\.org.*(EMD\-\d+)')
        with open(filename, 'rb') as fh:
            fh.seek(220) # Offset of number of labels
            num_labels_raw = fh.read(4)
            # Number of labels in MRC is usually a very small number, so it's
            # very likely to be the smaller of the big-endian and little-endian
            # interpretations of this field
            num_labels_big, = struct.unpack_from('>i', num_labels_raw)
            num_labels_little, = struct.unpack_from('<i', num_labels_raw)
            num_labels = min(num_labels_big, num_labels_little)
            for i in range(num_labels):
                label = fh.read(80).strip()
                m = r.search(label)
                if m:
                    if sys.version_info[0] < 3:
                        return m.group(1)
                    else:
                        return m.group(1).decode('ascii')
