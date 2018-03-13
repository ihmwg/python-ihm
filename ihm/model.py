"""Classes for handling models (sets of coordinates).
"""

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
