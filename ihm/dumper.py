"""Utility classes to dump out information in mmCIF format"""

import re
import ihm.format
from . import util

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


class _EntityPolyDumper(_Dumper):
    # todo: we currently only support amino acid sequences here
    def dump(self, system, writer):
        # Get the first asym unit (if any) for each entity
        strand = {}
        for asym in system.asym_units:
            if asym.entity.id not in strand:
                strand[asym.entity.id] = asym.id
        with writer.loop("_entity_poly",
                         ["entity_id", "type", "nstd_linkage",
                          "nstd_monomer", "pdbx_strand_id",
                          "pdbx_seq_one_letter_code",
                          "pdbx_seq_one_letter_code_can"]) as l:
            for entity in system.entities:
                seq = entity.sequence
                # Split into lines to get tidier CIF output
                seq = "\n".join(seq[i:i+70] for i in range(0, len(seq), 70))
                l.write(entity_id=entity.id, type='polypeptide(L)',
                        nstd_linkage='no', nstd_monomer='no',
                        pdbx_strand_id=strand.get(entity.id, None),
                        pdbx_seq_one_letter_code=seq,
                        pdbx_seq_one_letter_code_can=seq)


class _EntityPolySeqDumper(_Dumper):
    def dump(self, system, writer):
        with writer.loop("_entity_poly_seq",
                         ["entity_id", "num", "mon_id", "hetero"]) as l:
            for entity in system.entities:
                seq = entity.sequence
                for num, one_letter_code in enumerate(seq):
                    resid = _amino_acids[one_letter_code]
                    l.write(entity_id=entity.id, num=num + 1, mon_id=resid)


class _StructAsymDumper(_Dumper):
    def finalize(self, system):
        ordinal = 1
        # Assign asym IDs
        for asym, asym_id in zip(system.asym_units, util._AsymIDs()):
            asym.ordinal = ordinal
            asym.id = asym_id
            ordinal += 1

    def dump(self, system, writer):
        with writer.loop("_struct_asym",
                         ["id", "entity_id", "details"]) as l:
            for asym in system.asym_units:
                l.write(id=asym.id, entity_id=asym.entity.id,
                        details=asym.details)


class _AssemblyDumper(_Dumper):
    def finalize(self, system):
        # Fill in complete assembly
        system._make_complete_assembly()

        # Sort each assembly by entity/asym id
        def component_key(comp):
            return (comp.entity.id, comp.asym.ordinal if comp.asym else 0)
        for a in system.assemblies:
            a.sort(key=component_key)

        seen_assemblies = {}
        # Assign IDs to all assemblies; duplicate assemblies get same ID
        self._assembly_by_id = []
        for a in system.assemblies:
            # list isn't hashable but tuple is
            hasha = tuple(a)
            if hasha not in seen_assemblies:
                self._assembly_by_id.append(a)
                seen_assemblies[hasha] = a.id = len(self._assembly_by_id)
            else:
                a.id = seen_assemblies[hasha]

    def dump_details(self, system, writer):
        with writer.loop("_ihm_struct_assembly_details",
                         ["assembly_id", "assembly_name",
                          "assembly_description"]) as l:
            for a in self._assembly_by_id:
                l.write(assembly_id=a.id, assembly_name=a.name,
                        assembly_description=a.description)

    def dump(self, system, writer):
        self.dump_details(system, writer)
        ordinal = 1
        with writer.loop("_ihm_struct_assembly",
                         ["ordinal_id", "assembly_id", "parent_assembly_id",
                          "entity_description",
                          "entity_id", "asym_id", "seq_id_begin",
                          "seq_id_end"]) as l:
            for a in self._assembly_by_id:
                for comp in a:
                    entity = comp.entity
                    seqrange = comp.seq_id_range
                    l.write(ordinal_id=ordinal, assembly_id=a.id,
                            # if no hierarchy then assembly is self-parent
                            parent_assembly_id=a.parent.id if a.parent
                                               else a.id,
                            entity_description=entity.description,
                            entity_id=entity.id,
                            asym_id=comp.asym.id if comp.asym
                                                 else writer.omitted,
                            seq_id_begin=seqrange[0],
                            seq_id_end=seqrange[1])
                    ordinal += 1


def write(fh, systems):
    """Write out all `systems` to the mmCIF file handle `fh`"""
    dumpers = [_EntryDumper(), # must be first
               _SoftwareDumper(),
               _ChemCompDumper(),
               _EntityDumper(),
               _EntityPolyDumper(),
               _EntityPolySeqDumper(),
               _StructAsymDumper(),
               _AssemblyDumper()]
    writer = ihm.format.CifWriter(fh)
    for system in systems:
        for d in dumpers:
            d.finalize(system)
        for d in dumpers:
            d.dump(system, writer)
