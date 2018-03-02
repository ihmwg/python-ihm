"""Utility classes to dump out information in mmCIF format"""

import re
import ihm.format

# Standard amino acids, mapping from 1 to 3 letter codes
_amino_acids = {'A':'ALA', 'C':'CYS', 'D':'ASP', 'E':'GLU', 'F':'PHE',
                'G':'GLY', 'H':'HIS', 'I':'ILE', 'K':'LYS', 'L':'LEU',
                'M':'MET', 'N':'ASN', 'P':'PRO', 'Q':'GLN', 'R':'ARG',
                'S':'SER', 'T':'THR', 'V':'VAL', 'W':'TRP', 'Y':'TYR'}

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


class _SoftwareDumper(_Dumper):
    def dump(self, system, writer):
        ordinal = 1
        # todo: specify these attributes in only one place (e.g. in the Software
        # class)
        with writer.loop("_software",
                         ["pdbx_ordinal", "name", "classification",
                          "description", "version", "type", "location"]) as l:
            for s in system.software:
                l.write(pdbx_ordinal=ordinal, name=s.name,
                        classification=s.classification,
                        description=s.description, version=s.version,
                        type=s.type, location=s.location)
                ordinal += 1


class _ChemCompDumper(_Dumper):
    def dump(self, system, writer):
        seen = {}

        with writer.loop("_chem_comp", ["id", "type"]) as l:
            for entity in system.entities:
                seq = entity.sequence
                for num, one_letter_code in enumerate(seq):
                    resid = _amino_acids[one_letter_code]
                    if resid not in seen:
                        seen[resid] = None
                        l.write(id=resid, type='L-peptide linking')


class _EntityDumper(_Dumper):
    # todo: we currently only support amino acid sequences here (and
    # then only standard amino acids; need to add support for MSE etc.)

    def finalize(self, system):
        # Assign IDs and check for duplicates
        seen = {}
        for num, entity in enumerate(system.entities):
            if entity in seen:
                raise ValueError("Duplicate entity %s found" % entity)
            entity.id = num + 1
            seen[entity] = None

    def dump(self, system, writer):
        with writer.loop("_entity",
                         ["id", "type", "src_method", "pdbx_description",
                          "formula_weight", "pdbx_number_of_molecules",
                          "details"]) as l:
            for entity in system.entities:
                l.write(id=entity.id, type=entity.type,
			src_method=entity.src_method,
                        pdbx_description=entity.description,
                        formula_weight=entity.formula_weight,
                        pdbx_number_of_molecules=entity.number_of_molecules,
			details=entity.details)


def write(fh, systems):
    """Write out all `systems` to the mmCIF file handle `fh`"""
    dumpers = [_EntryDumper(), # must be first
               _SoftwareDumper(),
               _ChemCompDumper(),
               _EntityDumper()]
    writer = ihm.format.CifWriter(fh)
    for system in systems:
        for d in dumpers:
            d.finalize(system)
        for d in dumpers:
            d.dump(system, writer)
