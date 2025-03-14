#!/usr/bin/env python3

"""
Add minimal IHM-related tables to an mmCIF file.

Given any mmCIF file as input, this script will add any missing
IHM-related tables and write out a new file that is minimally compliant
with the IHM dictionary.

This is done by simply reading in the original file with python-ihm and
then writing it out again, so
  a) any data in the input file that is not understood by python-ihm
     will be lost on output; and
  b) input files that aren't compliant with the PDBx dictionary, or that
     contain syntax errors or other problems, may crash or otherwise confuse
     python-ihm.

The --add option can also be used to combine multiple input mmCIF files into
one. This is typically used when the mmCIF files contain models with
differing composition. Only model (coordinate) information is combined, not
other IHM information such as starting models or restraints.
"""


import ihm.reader
import ihm.dumper
import ihm.model
import ihm.protocol
import ihm.util
import os
import argparse


def add_ihm_info(s, fix_histidines):
    # Non-standard histidine names (protonation states)
    histidines = frozenset(('HIP', 'HID', 'HIE'))

    if not s.title:
        s.title = 'Auto-generated system'

    # Simple default assembly containing all chains
    default_assembly = ihm.Assembly(s.asym_units, name='Modeled assembly')

    # Simple default atomic representation for everything
    default_representation = ihm.representation.Representation(
        [ihm.representation.AtomicSegment(asym, rigid=False)
         for asym in s.asym_units])

    # Simple default modeling protocol
    default_protocol = ihm.protocol.Protocol(name='modeling')

    for state_group in s.state_groups:
        for state in state_group:
            for model_group in state:
                for model in model_group:
                    if not model.assembly:
                        model.assembly = default_assembly
                    if not model.representation:
                        model.representation = default_representation
                    if not model.protocol:
                        model.protocol = default_protocol
                    model.not_modeled_residue_ranges.extend(
                        _get_not_modeled_residues(model))
                    if fix_histidines:
                        _fix_histidine_het_atoms(model, histidines)
    if fix_histidines:
        _fix_histidine_chem_comps(s, histidines)
    return s


def _fix_histidine_het_atoms(model, histidines):
    """Fix any non-standard histidine atoms in atom_site that are marked
       HETATM to instead use ATOM"""
    for atom in model._atoms:
        if atom.seq_id is None or not atom.het:
            continue
        comp = atom.asym_unit.sequence[atom.seq_id - 1]
        if comp.id in histidines:
            atom.het = False


def _fix_histidine_chem_comps(s, histidines):
    """Change any non-standard histidine chemical components to normal HIS"""
    his = ihm.LPeptideAlphabet()['H']
    for e in s.entities:
        for c in e.sequence:
            if c.id in histidines:
                # Change the ChemComp to HIS in place, as there may be
                # references to this ChemComp elsewhere. Duplicate HIS
                # components will be combined into one at output time.
                c.id = his.id
                c.code = his.code
                c.code_canonical = his.code_canonical
                c.name = his.name
                c.formula = his.formula
                c.__class__ = his.__class__


def _get_not_modeled_residues(model):
    """Yield NotModeledResidueRange objects for all residue ranges in the
       Model that are not referenced by Atom, Sphere, or pre-existing
       NotModeledResidueRange objects"""
    for assem in model.assembly:
        asym = assem.asym if hasattr(assem, 'asym') else assem
        if not asym.entity.is_polymeric():
            continue
        # Make a set of all residue indices of this asym "handled" either
        # by being modeled (with Atom or Sphere objects) or by being
        # explicitly marked as not-modeled
        handled_residues = set()
        for rr in model.not_modeled_residue_ranges:
            if rr.asym_unit is asym:
                for seq_id in range(rr.seq_id_begin, rr.seq_id_end + 1):
                    handled_residues.add(seq_id)
        for atom in model._atoms:
            if atom.asym_unit is asym:
                handled_residues.add(atom.seq_id)
        for sphere in model._spheres:
            if sphere.asym_unit is asym:
                for seq_id in range(sphere.seq_id_range[0],
                                    sphere.seq_id_range[1] + 1):
                    handled_residues.add(seq_id)
        # Convert set to a list of residue ranges
        handled_residues = ihm.util._make_range_from_list(
            sorted(handled_residues))
        # Return not-modeled for each non-handled range
        for r in ihm.util._invert_ranges(handled_residues,
                                         end=assem.seq_id_range[1],
                                         start=assem.seq_id_range[0]):
            yield ihm.model.NotModeledResidueRange(asym, r[0], r[1])


def add_ihm_info_one_system(fname, fix_histidines):
    """Read mmCIF file `fname`, which must contain a single System, and
       return it with any missing IHM data added."""
    with open(fname) as fh:
        systems = ihm.reader.read(fh)
    if len(systems) != 1:
        raise ValueError("mmCIF file %s must contain exactly 1 data block "
                         "(%d found)" % (fname, len(systems)))
    return add_ihm_info(systems[0], fix_histidines)


def combine(s, other_s):
    """Add models from the System `other_s` into the System `s`.
       After running this function, `s` will contain all Models from both
       systems. The models are added to new StateGroup(s) in `s`.
       Note that this function also modifies `other_s` in place, so that
       System should no longer be used after calling this function."""
    # First map all Entity and AsymUnit objects in `other_s` to equivalent
    # objects in `s`
    entity_map = combine_entities(s, other_s)
    asym_map = combine_asyms(s, other_s, entity_map)
    # Now handle the Models themselves
    combine_atoms(s, other_s, asym_map)


def combine_entities(s, other_s):
    """Add `other_s` entities into `s`. Returns a dict that maps Entities
       in `other_s` to equivalent objects in `s`."""
    entity_map = {}
    sequences = dict((e.sequence, e) for e in s.entities)
    for e in other_s.entities:
        if e.sequence in sequences:
            # If the `other_s` Entity already exists in `s`, map to it
            entity_map[e] = sequences[e.sequence]
        else:
            # Otherwise, add the `other_s` Entity to `s`
            s.entities.append(e)
            entity_map[e] = e
    return entity_map


def combine_asyms(s, other_s, entity_map):
    """Add `other_s` asyms into `s`. Returns a dict that maps AsymUnits
       in `other_s` to equivalent objects in `s`."""
    asym_map = {}
    # Collect author-provided information for existing asyms. For polymers,
    # we use the author-provided chain ID; for non-polymers, we also use
    # the author-provided residue number of the first (only) residue
    poly_asyms = dict(((a.entity, a.strand_id), a)
                      for a in s.asym_units if a.entity.is_polymeric())
    nonpoly_asyms = dict(((a.entity, a.strand_id, a.auth_seq_id_map[1]), a)
                         for a in s.asym_units
                         if a.entity.type == 'non-polymer')

    def map_asym(asym, orig_asym):
        if orig_asym:
            # If an equivalent asym already exists, use it (and its asym_id)
            asym_map[asym] = orig_asym
        else:
            # Otherwise, add a new asym
            asym_map[asym] = asym
            asym.id = None  # Assign new ID
            s.asym_units.append(asym)

    for asym in other_s.asym_units:
        # Point to Entity in `s`, not `other_s`
        asym.entity = entity_map[asym.entity]
        # For polymers and non-polymers, if an asym in `other_s` has the
        # same author-provided information and entity_id as an asym in `s`,
        # reuse the asym_id
        if asym.entity.is_polymeric():
            map_asym(asym, poly_asyms.get((asym.entity, asym.strand_id)))
        elif asym.entity.type == 'non-polymer':
            map_asym(asym, nonpoly_asyms.get((asym.entity, asym.strand_id,
                                              asym.auth_seq_id_map[1])))
        else:
            # For waters and branched entities, always assign a new asym_id
            asym_map[asym] = asym
            asym.id = None  # Assign new ID
            s.asym_units.append(asym)
    return asym_map


def combine_atoms(s, other_s, asym_map):
    """Add `other_s` atoms into `s`"""
    seen_asmb = set()
    seen_rep = set()
    for state_group in other_s.state_groups:
        for state in state_group:
            for model_group in state:
                for model in model_group:
                    # Assembly, Representation and Atom and Sphere objects
                    # all reference `other_s` asyms. We must map these to
                    # asyms in `s`.
                    asmb = model.assembly
                    if id(asmb) not in seen_asmb:
                        seen_asmb.add(id(asmb))
                        # todo: also handle AsymUnitRange
                        asmb[:] = [asym_map[asym] for asym in asmb]
                    rep = model.representation
                    if id(rep) not in seen_rep:
                        seen_rep.add(id(rep))
                        for seg in rep:
                            seg.asym_unit = asym_map[seg.asym_unit]
                    for atom in model._atoms:
                        atom.asym_unit = asym_map[atom.asym_unit]
                    for sphere in model._spheres:
                        sphere.asym_unit = asym_map[sphere.asym_unit]

    # Add all models as new state groups
    s.state_groups.extend(other_s.state_groups)


def get_args():
    p = argparse.ArgumentParser(
        description="Add minimal IHM-related tables to an mmCIF file.")
    p.add_argument("input", metavar="input.cif", help="input mmCIF file name")
    p.add_argument("output", metavar="output.cif",
                   help="output mmCIF file name",
                   default="output.cif", nargs="?")
    p.add_argument("--add", "-a", action='append', metavar="add.cif",
                   help="also add model information from the named mmCIF "
                        "file to the output file")
    p.add_argument("--histidines", action='store_true', dest="fix_histidines",
                   help="Convert any non-standard histidine names (HIP, HID, "
                        "HIE, for different protonation states) to HIS")
    return p.parse_args()


def main():
    args = get_args()

    if (os.path.exists(args.input) and os.path.exists(args.output)
            and os.path.samefile(args.input, args.output)):
        raise ValueError("Input and output are the same file")

    if args.add:
        s = add_ihm_info_one_system(args.input, args.fix_histidines)
        for other in args.add:
            other_s = add_ihm_info_one_system(other, args.fix_histidines)
            combine(s, other_s)
        with open(args.output, 'w') as fhout:
            ihm.dumper.write(
                fhout, [s],
                variant=ihm.dumper.IgnoreVariant(['_audit_conform']))
    else:
        with open(args.input) as fh:
            with open(args.output, 'w') as fhout:
                ihm.dumper.write(
                    fhout, [add_ihm_info(s, args.fix_histidines)
                            for s in ihm.reader.read(fh)],
                    variant=ihm.dumper.IgnoreVariant(['_audit_conform']))


if __name__ == '__main__':
    main()
