"""Representation of an IHM mmCIF file as a set of Python classes.

   Generally class names correspond to mmCIF table names and class
   attributes to mmCIF attributes (with prefixes like pdbx_ stripped).
   For example, the data item _entity.details is found in the
   :class:`Entity` class, as the `details` member.

   Ordinals and IDs are generally not used in this representation (instead,
   pointers to objects are used).
"""

from .format import CifWriter

#: A value that isn't known. Note that this is distinct from a value that
#: is deliberately omitted, which is represented by Python None.
unknown = CifWriter.unknown

class System(object):
    """Top-level class representing a complete modeled system"""

    def __init__(self, name='model'):
        self.name = name

        #: List of all software used in the modeling. See :class:`Software`.
        self.software = []

        #: All entities used in the system. See :class:`Entity`.
        self.entities = []

        #: All asymmetric units used in the system. See :class:`AsymUnit`.
        self.asym_units = []

        #: All assemblies used in the system. See :class:`Assembly`.
        self.assemblies = []


class Software(object):
    """Software used as part of the modeling protocol.

       See :attr:`System.software`."""
    def __init__(self, name, classification, description, location,
                 type='program', version=None):
        self.name = name
        self.classification = classification
        self.description = description
        self.location = location
        self.type = type
        self.version = version


class Entity(object):
    """Represent a CIF entity (with a unique sequence)

       See :attr:`System.entities`.

       Note that currently only standard amino acids are supported.
    """

    type = 'polymer'
    src_method = 'man'
    number_of_molecules = 1
    formula_weight = unknown

    def __init__(self, seq, description=None, details=None):
        self.sequence = seq
        self.description, self.details = description, details

    # Entities are considered identical if they have the same sequence
    def __eq__(self, other):
        return self.sequence == other.sequence
    def __hash__(self):
        return hash(self.sequence)


class AsymUnit(object):
    """An asymmetric unit, i.e. a unique instance of an Entity that
       was modeled.

       See :attr:`System.asym_units`.
    """

    def __init__(self, entity, details=None):
        self.entity, self.details = entity, details


class AssemblyComponent(object):
    """A single component in an :class:`Assembly`.

       :param component: The part of the system. :class:`Entity` can be used
                         here for a part that is known but has no structure.
       :type component: :class:`AsymUnit` or :class:`Entity`
       :param tuple seq_id_range: The subset of the sequence range to include in
                         the assembly. This should be a two-element tuple.
                         If `None` (the default) the entire range is included.
    """

    def __init__(self, component, seq_id_range=None):
        self.component, self._seqrange = component, seq_id_range

    def __get_seqrange(self):
        if self._seqrange:
            return self._seqrange
        elif isinstance(self.component, Entity):
            return (1, len(self.component.sequence))
        else:
            return (1, len(self.component.entity.sequence))
    seq_id_range = property(__get_seqrange, doc="Sequence range")


class Assembly(list):
    """A collection of parts of the system that were modeled or probed
       together.

       This is implemented as a simple list of :class:`AssemblyComponent`
       objects.

       See :attr:`System.assemblies`.

       Note that any duplicate assemblies will be pruned on output."""

    #: Another :class:`Assembly` that is the immediate parent in a hierarchy        #: of assemblies, or `None` if no hierarchy is present.
    parent = None

    def __init__(self, elements=(), name=None, description=None):
        super(Assembly, self).__init__(elements)
        self.name, self.description = name, description
