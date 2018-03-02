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


class Software(object):
    """Software used as part of the modeling protocol.

       See :memb:`System.software`."""
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

       See :memb:`System.entities`.

       Note that currently only standard amino acids are supported.
    """

    type = 'polymer'
    src_method = 'man'
    number_of_molecules = 1
    formula_weight = unknown

    def __init__(self, seq, description=None, details=None):
        self.sequence = tuple(seq) # sequence should be immutable
        self.description, self.details = description, details

    # Entities are considered identical if they have the same sequence
    def __eq__(self, other):
        return self.sequence == other.sequence
    def __hash__(self):
        return hash(self.sequence)
