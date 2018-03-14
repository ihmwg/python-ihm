"""Classes for handling restraints on the system.
"""

class Restraint(object):
    """Base class for all restraints.
       See :attr:`ihm.System.restraints`.
    """
    pass


class EM3DRestraint(Restraint):
    """Restrain part of the system to match an electron microscopy density map.

       :param dataset: Reference to the density map data (usually
              an :class:`~ihm.dataset.EMDensityDataset`).
       :type dataset: :class:`~ihm.dataset.Dataset`
       :param assembly: The part of the system that is fit into the map.
       :type assembly: :class:`~ihm.Assembly`
       :param bool segment: True iff the map has been segmented.
       :param str fitting_method: The method used to fit the model into the map.
       :param int number_of_gaussians: Number of Gaussians used to represent
              the map as a Gaussian Mixture Model (GMM), if applicable.
       :param str details: Addition details regarding the fitting.
    """

    def __init__(self, dataset, assembly, segment=None, fitting_method=None,
                 number_of_gaussians=None, details=None):
        self.dataset, self.assembly = dataset, assembly
        self.segment, self.fitting_method = segment, fitting_method
        self.number_of_gaussians = number_of_gaussians
        self.details = details

        #: Information about the fit of each model to this restraint's data.
        #: This is a Python dict where keys are :class:`~ihm.model.Model`
        #: objects and values are :class:`EM3DRestraintFit` objects.
        self.fits = {}


class EM3DRestraintFit(object):
    """Information on the fit of a model to an :class:`EM3DRestraint`.
       See :attr:`EM3DRestaint.fits`.

       :param float cross_correlation_coefficient: The fit between the model
              and the map.
    """
    __slots__ = ["cross_correlation_coefficient"] # Reduce memory usage

    def __init__(self, cross_correlation_coefficient=None):
        self.cross_correlation_coefficient = cross_correlation_coefficient
