"""Classes for handling models (sets of coordinates).
"""

class Sphere(object):
    """Coordinates of part of the model represented by a sphere.

       :param asym_unit: The asymmetric unit that this sphere represents
       :type asym_unit: :class:`ihm.AsymUnit`
       :param tuple seq_id_range: The range of residues represented by this
              sphere (as a two-element tuple)
       :param float x: x coordinate of the center of the sphere
       :param float y: y coordinate of the center of the sphere
       :param float z: z coordinate of the center of the sphere
       :param float radius: radius of the sphere
       :param float rmsf: root-mean-square fluctuation of the coordinates
    """

    # Reduce memory usage
    __slots__ = ['asym_unit', 'seq_id_range', 'x', 'y', 'z', 'radius', 'rmsf']

    def __init__(self, asym_unit, seq_id_range, x, y, z, radius, rmsf=None):
        self.asym_unit = asym_unit
        self.seq_id_range = seq_id_range
        self.x, self.y, self.z = x, y, z
        self.radius, self.rmsf = radius, rmsf


class Model(object):
    """A single set of coordinates (conformation).

       See :class:`ModelGroup`.

       :param assembly: The parts of the system that were modeled.
       :type assembly: :class:`~ihm.Assembly`
       :param protocol: Description of how the modeling was done.
       :type protocol: :class:`~ihm.protocol.Protocol`
       :param representation: Level of detail at which the system
              was represented.
       :type representation: :class:`~ihm.representation.Representation`
       :param str name: Descriptive name for this model.
    """
    def __init__(self, assembly, protocol, representation, name=None):
        self.assembly, self.protocol = assembly, protocol
        self.representation, self.name = representation, name
        self._spheres = []

    def get_spheres(self):
        """Yield :class:`Sphere` objects that represent this model.

           The default implementation simply iterates over an internal
           list of spheres, but this is not very memory-efficient, particularly
           if the spheres are already stored somewhere else, e.g. in the
           software's own data structures. It is recommended to subclass
           and provide a more efficient implementation.

           Note that the set of spheres should match the model's
           :class:`~ihm.representation.Representation`. This is not currently
           enforced.
        """
        for s in self._spheres:
            yield s

    def set_spheres(self, spheregen):
        """Populate the model's set of :class:`Sphere` objects from the
           given Python generator.

           See :meth:`get_spheres` for more details.
        """
        self._spheres = [s for s in spheregen]


class ModelGroup(list):
    """A set of related models. See :class:`Model` and
       :attr:`ihm.System.model_groups`. It is implemented as a simple
       list of the models.

       :param elements: Initial set of models in the group.
       :param str name: Descriptive name for the group.
    """
    def __init__(self, elements=(), name=None):
        self.name = name
        super(ModelGroup, self).__init__(elements)
