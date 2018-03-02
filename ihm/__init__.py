"""Representation of an IHM mmCIF file as a set of Python classes."""

class System(object):
    """Top-level class representing a complete modeled system"""

    def __init__(self, name='model'):
        self.name = name
