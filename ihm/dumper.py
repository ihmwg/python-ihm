"""Utility classes to dump out information in mmCIF format"""

import re
import ihm.format

class _Dumper(object):
    """Base class for helpers to dump output to mmCIF"""
    def __init__(self):
        pass
    def finalize(self, system):
        """Called for all dumpers prior to `dump` - can assign IDs, etc"""
        pass
    def dump(self, system, writer):
        """Use `writer` to write information about `system` to mmCIF"""
        pass


class _EntryDumper(_Dumper):
    def dump(self, system, writer):
        # Write CIF header (so this dumper should always be first)
        writer.fh.write("data_%s\n" % re.subn('[^0-9a-zA-z_]', '',
                                              system.name)[0])
        with writer.category("_entry") as l:
            l.write(id=system.name)


def write(fh, systems):
    """Write out all `systems` to the mmCIF file handle `fh`"""
    dumpers = [_EntryDumper()] # must be first
    writer = ihm.format.CifWriter(fh)
    for system in systems:
        for d in dumpers:
            d.finalize(system)
        for d in dumpers:
            d.dump(system, writer)
