"""Classes for handling experimental datasets used by mmCIF models.
"""

try:
    from collections import OrderedDict
except ImportError:
    from ._compat_collections import OrderedDict


class Dataset(object):
    """A set of input data, for example, a crystal structure or EM map."""

    _eq_keys = ['location']

    # Datasets compare equal iff they are the same class and have the
    # same attributes
    def _eq_vals(self):
        return tuple([self.__class__]
                     + [getattr(self, x) for x in self._eq_keys])
    def __eq__(self, other):
        return self._eq_vals() == other._eq_vals()
    def __hash__(self):
        return hash(self._eq_vals())

    data_type = 'unspecified'
    def __init__(self, location):
        self.location = location
        self._parents = OrderedDict()

    def add_parent(self, dataset):
        """Add another :class:`Dataset` from which this one was derived.
           For example, a 3D EM map may be derived from a set of 2D images."""
        self._parents[dataset] = None


class CXMSDataset(Dataset):
    """Processed crosslinks from a CX-MS experiment"""
    data_type = 'CX-MS data'


class MassSpecDataset(Dataset):
    """Raw mass spectrometry files such as peaklists"""
    data_type = 'Mass Spectrometry data'


class PDBDataset(Dataset):
    """An experimentally-determined 3D structure as a set of a coordinates,
       usually in a PDB file"""
    data_type = 'Experimental model'


class ComparativeModelDataset(Dataset):
    """A 3D structure determined by comparative modeling"""
    data_type = 'Comparative model'


class IntegrativeModelDataset(Dataset):
    """A 3D structure determined by integrative modeling"""
    data_type = 'Integrative model'


class EMDensityDataset(Dataset):
    """A 3D electron microscopy dataset"""
    data_type = '3DEM volume'


class EM2DClassDataset(Dataset):
    """2DEM class average"""
    data_type = '2DEM class average'


class SASDataset(Dataset):
    """SAS data"""
    data_type = 'SAS data'
