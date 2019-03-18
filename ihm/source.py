"""Classes for describing the source of an entity.
"""

class Source(object):
    """Base class to describe the source of an :class:`ihm.Entity`.
       See :class:`Manipulated`, :class:`Natural` and :class:`Synthetic`.
    """
    src_method = None


class Manipulated(Source):
    """An entity isolated from a genetically manipulated source.
       See :class:`Entity`."""
    src_method = 'man'


class Natural(Source):
    """An entity isolated from a natural source. See :class:`Entity`."""
    src_method = 'nat'


class Synthetic(Source):
    """An entity obtained synthetically. See :class:`Entity`."""
    src_method = 'syn'
