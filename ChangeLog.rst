0.29 - 2022-04-01
=================
  - Output mmCIF files containing non-polymers should now validate against
    the PDBx dictionary (#76).
  - Bugfix: non-polymers that are erroneously marked as polymers in
    the input mmCIF can now be read in without causing a Python
    exception (#78).
  - Bugfix: strings starting with an underscore (e.g. chain names) are now
    quoted in mmCIF output to conform to the CIF syntax (#75).

0.28 - 2022-03-21
=================
  - :class:`ihm.Citation` now takes a ``is_primary`` argument, which can
    be used to denote the most pertinent publication for the modeling.
  - Improved support for non-standard residues, and for standard amino acids
    used as nonpolymers.

0.27 - 2022-01-27
=================
  - Minor documentation improvements.
  - Add support for the _struct.pdbx_structure_determination_methodology
    mmCIF data item.

0.26 - 2022-01-12
=================
  - :func:`ihm.dumper.write` and :func:`ihm.reader.read` both now take
    a ``variant`` argument which can be used to control the set of tables
    that are read/written. This can be used by other libraries (such as
    python-ma) to support other mmCIF extensions.

0.25 - 2021-12-03
=================
  - :func:`ihm.dictionary.Dictionary.validate` will now report errors for
    any keywords or categories in the file that are not present in the
    dictionary.
  - :class:`ihm.LPeptideAlphabet` now supports the ASX and GLX ambiguous
    residue types.

0.24 - 2021-12-01
=================
  - :class:`ihm.AsymUnit` now supports insertion codes in its
    ``auth_seq_id_map``. The target of this mapping can either be an
    author-provided residue number (as previously) or a 2-element tuple
    containing this number and an insertion code.
  - :class:`ihm.AsymUnit` now allows the PDB or author-provided strand/chain ID
    to be different from the regular ID.
  - Bugfix: if two :class:`ihm.dictionary.Dictionary` objects both contain
    information about a given category, adding the two dictionaries together
    now combines the category information, rather than just using that from
    one dictionary.
  - Bugfix: :class:`ihm.dictionary.Dictionary` should now be able to validate
    BinaryCIF files containing integer or float values (#66).

0.23 - 2021-11-01
=================
  - Bugfix: _struct_ref.pdbx_seq_one_letter_code is now treated as the subset
    of the reference (e.g. UniProt) sequence that overlaps with our Entities,
    not the entire sequence (#64).

0.22 - 2021-10-22
=================
  - The :class:`ihm.Software` class now allows a citation for the software
    to be provided.
  - A new :mod:`ihm.citations` module contains citations for some packages
    that are commonly used in integrative modeling.

0.21 - 2021-07-14
=================
  - BinaryCIF files now use UTF8 msgpack strings for all text, rather than
    raw bytes. This should make python-ihm's BinaryCIF files interoperable
    with those used by, e.g., CoordinateServer.
  - Output mmCIF files now include author-provided numbering (auth_seq_id)
    for atoms in the atom_site table. This should help packages that don't
    read the pdbx_poly_seq_scheme table to show the desired residue
    numbering (#61).

0.20 - 2021-05-06
=================
  - Support for Python 2.6 has been dropped. The library needs Python 2.7
    or Python 3.
  - Bugfix: correctly read in multiline reference sequence one-letter codes.
  - Bugfix: the reader is now more tolerant of omitted or unknown values
    (. or ?) in input mmCIF files.

0.19 - 2021-04-16
=================
  - A convenience class is added to describe datasets stored in the
    ProXL database (:class:`ihm.location.ProXLLocation`).

0.18 - 2020-11-06
=================
  - Update to match latest FLR dictionary.
  - Add a simple utility (util/make-mmcif.py) to make a minimal compliant
    IHM mmCIF file, given an mmCIF file (potentially just coordinates) as input.
  - Bugfix: the full residue range spanned by a starting model is now reported,
    rather than just the subset that is mapped to one or more templates (#55).
  - Bugfix: handle TrEMBL UniProt sequences (#57).

0.17 - 2020-07-10
=================
  - Convenience classes are added to describe hydrogen/deuterium exchange
    data (:class:`ihm.dataset.HDXDataset`) and datasets stored in the
    PDB-Dev database (:class:`ihm.location.PDBDevLocation`).
  - Multiple :class:`ihm.restraint.CrossLinkPseudoSite` objects can now
    be assigned to a given :class:`ihm.restraint.CrossLink`.
  - Bugfix: the :class:`ihm.dataset.Dataset` base class now has a type
    of "Other" rather than "unspecified" to conform with the latest
    IHM dictionary.

0.16 - 2020-05-29
=================
  - :func:`ihm.reader.read` no longer discards models read from non-IHM mmCIF
    files; they are instead placed in their own :class:`ihm.model.ModelGroup`.
  - Bugfix: both the pure Python and C-accelerated mmCIF readers are now more
    robust, able to handle files in binary mode (e.g. from opening a URL)
    and in Unicode (mmCIF files are supposed to be ASCII but python-ihm should
    handle any encoding Python supports).

0.15 - 2020-04-14
=================
  - :class:`ihm.dataset.Dataset` objects that derive from another dataset
    can now record any transformation involved; see
    :class:`ihm.dataset.TransformedDataset`.
  - :class:`ihm.metadata.PDBParser` now extracts basic metadata from
    PDB files generated by SWISS-MODEL.
  - An :class:`ihm.Entity` can now be linked to one or more reference databases
    (e.g. UniProt). See the classes in the :mod:`ihm.reference` module.

0.14 - 2020-02-26
=================
 - A cross-link can now use pseudo sites to represent one or both ends of the
   link. The new :class:`ihm.restraint.CrossLinkPseudoSite` object is used
   when the end of the cross-link is not represented in the model but its
   position is known (e.g. it may have been approximated given the position
   of nearby residues).
 - :class:`ihm.restraint.PseudoSiteFeature` now references an underlying
   :class:`ihm.restraint.PseudoSite`, allowing a single pseudo site to be
   shared between a feature and a cross-link if desired.
 - :class:`ihm.model.Ensemble` now supports describing subsamples from which
   the ensemble was constructed; see :class:`ihm.model.Subsample`.
 - Bugfix: :meth:`ihm.Citation.from_pubmed_id` now works correctly when the
   journal volume or page range are empty, or the page "range" is just a
   single page.

0.13 - 2019-11-14
=================
 - :func:`ihm.reader.read` has a new optional ``reject_old_file`` argument.
   If set, it will raise an exception if asked to read a file that conforms
   to too old a version of the IHM extension dictionary.
 - Definitions for the DHSO and BMSO cross-linkers are now provided in the
   :mod:`ihm.cross_linkers` module.

0.12 - 2019-10-16
=================
 - :class:`ihm.restraint.ResidueFeature` objects can now act on one or
   more :class:`Residue` objects, which act equivalently to
   1-residue ranges (:class:`AsymUnitRange` or :class:`EntityRange`).
 - The new :class:`ihm.dataset.GeneticInteractionsDataset` class and the
   ``mic_value`` argument to :class:`ihm.restraint.DerivedDistanceRestraint`
   can be used to represent restraints from genetic interactions, such as
   point-mutant epistatic miniarray profile (pE-MAP) data.

0.11 - 2019-09-05
=================
 - :class:`ihm.Assembly` objects can now only contain :class:`AsymUnit`
   and :class:`AsymUnitRange` objects (not :class:`Entity` or
   :class:`EntityRange`).
 - Bugfix: ensembles that don't reference a :class:`ihm.model.ModelGroup`
   no longer cause the reader to create bogus empty model groups.

0.10 - 2019-07-09
=================
 - Features (:class:`ihm.restraint.AtomFeature`,
   :class:`ihm.restraint.ResidueFeature`, and
   :class:`ihm.restraint.NonPolyFeature`), which previously could select part
   or all of an :class:`ihm.AsymUnit`, can now also select parts of an
   :class:`Entity`. A restraint acting on an entity-feature is assumed
   to apply to all instances of that entity.

0.9 - 2019-05-31
================
 - Add support for the latest version of the IHM dictionary.

0.8 - 2019-05-28
================
 - :func:`ihm.reader.read` can now be asked to warn if it encounters
   categories or keywords in the mmCIF or BinaryCIF file that it doesn't
   know about (and will ignore).
 - Predicted contacts (:class:`ihm.restraint.PredictedContactRestraint`)
   are now supported.
 - :func:`ihm.reader.read` will now read starting model coordinates and
   sequence difference information into the
   :class:`ihm.startmodel.StartingModel` class. Applications that don't require
   coordinates can instruct the reader to ignore them with the new
   `read_starting_model_coord` flag.
 - The new :mod:`ihm.flr` module allows for information from
   Fluorescence / FRET experiments to be stored. This follows the definitions
   in the `FLR dictionary <https://github.com/ihmwg/FLR-dictionary/>`_.

0.7 - 2019-04-24
================
 - Authors of the mmCIF file itself (`_audit_author` category) can now be
   set by manipulating :attr:`ihm.System.authors`. (If this list is empty on
   output, the set of all citation authors is used instead, as before.)
 - Any grants that supported the modeling can now be listed in
   :attr:`ihm.System.grants`.
 - A copy of `SWIG <http://www.swig.org/>`_ is no longer needed to install
   releases of python-ihm via `pip` as pre-generated SWIG outputs are
   included in the PyPI package. SWIG is still needed to build directly
   from source code though.

0.6 - 2019-03-22
================
 - :class:`Entity` now takes an optional :class:`ihm.source.Source` object to
   describe the method by which the sample for the entity was produced.
   :class:`ihm.metadata.PDBParser` will also extract this information
   from input PDB files.
 - :func:`ihm.reader.read` and :func:`ihm.dumper.write` now support reading
   or writing additional user-defined mmCIF categories.

0.5 - 2019-01-17
================
 - :class:`ihm.restraint.CrossLinkRestraint` now takes an
   :class:`ihm.ChemDescriptor` object rather than the name of the cross-linker
   used. This allows the use of novel cross-linkers (beyond those currently
   listed in a fixed enumeration in the IHM dictionary).
   :class:`ihm.ChemDescriptor` allows for the chemical structure of the
   cross-linker to be uniquely specified, as a SMILES or INCHI string.
   The :mod:`ihm.cross_linkers` module provides chemical descriptors for
   some commonly-used cross-linkers.
 - Pseudo sites are now supported. :class:`ihm.restraint.PseudoSiteFeature`
   allows points or spheres with arbitrary coordinates to be designated as
   features, which can then be used in
   :class:`ihm.restraint.DerivedDistanceRestraint`.

0.4 - 2018-12-17
================
 - Certain restraints can now be grouped using the
   :class:`ihm.restraint.RestraintGroup` class. Due to limitations of the
   underlying dictionary, this only works for some restraint types (currently
   only :class:`ihm.restraint.DerivedDistanceRestraint`) and all restraints
   in the group must be of the same type.
 - Bugfix: the model's representation (see :mod:`ihm.representation`)
   need not be a strict subset of the model's :class:`ihm.Assembly`. However,
   any :class:`ihm.model.Atom` or :class:`ihm.model.Sphere` objects must be
   covered by both the representation and the model's :class:`ihm.Assembly`.
 - Bugfix: the reader no longer fails to read files that contain
   _entity.formula_weight.

0.3 - 2018-11-21
================

 - The library now includes basic support for nonpolymers and water molecules.
   In addition to the previous support for polymers (amino or nucleic acid
   chains), :class:`ihm.Entity` objects can now comprise ligands, water
   molecules, and user-defined chemical components.
 - The library can now read mmCIF dictionaries and validate mmCIF or BinaryCIF
   files against them. See :mod:`ihm.dictionary`.
 - Any :class:`ihm.model.Atom` or :class:`ihm.model.Sphere` objects are now
   checked against the model's representation (see :mod:`ihm.representation`);
   for example, an :class:`ihm.model.Atom` must correspond to an
   :class:`ihm.representation.AtomicSegment`. The representation in turn must
   be a subset of the model's :class:`ihm.Assembly`.
 - More examples are now provided, of creating and using non-standard residue
   types (chemical components); representing nonpolymers; and using the C
   mmCIF parser in other C programs.

0.2 - 2018-09-06
================

 - This release should fix installation of the package using pip:
   `pip install ihm` should now work correctly.

0.1 - 2018-09-06
================

 - First stable release. This provides largely complete support for the current
   version of the wwPDB IHM mmCIF extension dictionary, and will read and
   write mmCIF and BinaryCIF files that are compliant with the PDBx and
   IHM dictionaries.

