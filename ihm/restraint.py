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


class SASRestraint(Restraint):
    """Restrain part of the system to match small angle scattering (SAS) data.

       :param dataset: Reference to the SAS data (usually
              an :class:`~ihm.dataset.SASDataset`).
       :type dataset: :class:`~ihm.dataset.Dataset`
       :param assembly: The part of the system that is fit against SAS data.
       :type assembly: :class:`~ihm.Assembly`
       :param bool segment: True iff the SAS profile has been segmented.
       :param str fitting_method: The method used to fit the model against the
              SAS data (e.g. FoXS, DAMMIF).
       :param str fitting_atom_type: The set of atoms fit against the data
              (e.g. "Heavy atoms", "All atoms").
       :param bool multi_state: Whether multiple state fitting was done.
       :param float radius_of_gyration: Radius of gyration obtained from the
              SAS profile, if used as part of the restraint.
       :param str details: Addition details regarding the fitting.
    """

    def __init__(self, dataset, assembly, segment=None, fitting_method=None,
                 fitting_atom_type=None, multi_state=None,
                 radius_of_gyration=None, details=None):
        self.dataset, self.assembly = dataset, assembly
        self.segment, self.fitting_method = segment, fitting_method
        self.fitting_atom_type = fitting_atom_type
        self.multi_state = multi_state
        self.radius_of_gyration = radius_of_gyration
        self.details = details

        #: Information about the fit of each model to this restraint's data.
        #: This is a Python dict where keys are :class:`~ihm.model.Model`
        #: objects and values are :class:`SASRestraintFit` objects.
        self.fits = {}


class SASRestraintFit(object):
    """Information on the fit of a model to a :class:`SASRestraint`.
       See :attr:`SASRestaint.fits`.

       :param float chi_value: The fit between the model and the SAS data.
    """
    __slots__ = ["chi_value"] # Reduce memory usage

    def __init__(self, chi_value=None):
        self.chi_value = chi_value
