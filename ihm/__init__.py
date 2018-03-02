"""Representation of an IHM mmCIF file as a set of Python classes."""

class System(object):
    """Top-level class representing a complete modeled system"""

    def __init__(self, name='model'):
        self.name = name

        #: List of all software used in the modeling. See :class:`Software`.
        self.software = []


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
