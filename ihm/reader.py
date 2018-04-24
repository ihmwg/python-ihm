"""Utility classes to read in information in mmCIF format"""

import ihm.format
import ihm.location
import ihm.dataset
import inspect

def _make_new_entity():
    """Make a new Entity object"""
    e = ihm.Entity([])
    # make sequence mutable
    e.sequence = list(e.sequence)
    return e

class _IDMapper(object):
    """Handle mapping from mmCIF IDs to Python objects.

       :param list system_list: The list in :class:`ihm.System` that keeps
              track of these objects.
       :param class cls: The base class for the Python objects.
    """

    # The attribute in the class used to store the ID
    id_attr = '_id'

    def __init__(self, system_list, cls, *cls_args, **cls_keys):
        self.system_list = system_list
        self._obj_by_id = {}
        self._cls = cls
        self._cls_args = cls_args
        self._cls_keys = cls_keys

    def get_by_id(self, objid, newcls=None):
        """Get the object with given ID, creating it if it doesn't already
           exist."""
        if objid in self._obj_by_id:
            obj = self._obj_by_id[objid]
            # If this object was referenced by another table before it was
            # created, it may have the wrong class - fix that retroactively
            # (need to be careful that old and new classes are compatible)
            if newcls:
                obj.__class__ = newcls
            return obj
        else:
            if newcls is None:
                newcls = self._cls
            newobj = newcls(*self._cls_args, **self._cls_keys)
            setattr(newobj, self.id_attr, objid)
            self._obj_by_id[objid] = newobj
            if self.system_list is not None:
                self.system_list.append(newobj)
            return newobj


class _ChemCompIDMapper(_IDMapper):
    """Add extra handling to _IDMapper for the chem_comp category"""

    id_attr = 'id'

    def __init__(self, *args, **keys):
        super(_ChemCompIDMapper, self).__init__(*args, **keys)
        # get standard residue types
        alphabets = [x[1] for x in inspect.getmembers(ihm, inspect.isclass)
                     if issubclass(x[1], ihm.Alphabet)
                     and x[1] is not ihm.Alphabet]
        self._standard_by_id = {}
        for alphabet in alphabets:
            self._standard_by_id.update((item[1].id, item[1])
                                        for item in alphabet._comps.items())

    def get_by_id(self, objid, newcls=None):
        # Don't modify class of standard residue types
        if objid in self._standard_by_id:
            return self._standard_by_id[objid]
        else:
            return super(_ChemCompIDMapper, self).get_by_id(objid, newcls)


class _SystemReader(object):
    """Track global information for a System being read from a file, such
       as the mapping from IDs to objects."""
    def __init__(self):
        self.system = ihm.System()
        self.software = _IDMapper(self.system.software, ihm.Software,
                                  *(None,)*4)
        self.citations = _IDMapper(self.system.citations, ihm.Citation,
                                   *(None,)*8)
        self.entities = _IDMapper(self.system.entities, _make_new_entity)
        self.asym_units = _IDMapper(self.system.asym_units, ihm.AsymUnit, None)
        self.chem_comps = _ChemCompIDMapper(None, ihm.ChemComp, *(None,)*3)
        self.assemblies = _IDMapper(self.system.orphan_assemblies, ihm.Assembly)
        self.repos = _IDMapper(None, ihm.location.Repository, None)
        self.external_files = _IDMapper(self.system.locations,
                                 ihm.location.FileLocation,
                                 '/') # should always exist?
        self.db_locations = _IDMapper(self.system.locations,
                                 ihm.location.DatabaseLocation, None, None)
        self.datasets = _IDMapper(self.system.orphan_datasets,
                                  ihm.dataset.Dataset, None)
        self.dataset_groups = _IDMapper(self.system.orphan_dataset_groups,
                                  ihm.dataset.DatasetGroup)


class _Handler(object):
    """Base class for all handlers of mmCIF data."""
    def __init__(self, sysr):
        self.sysr = sysr

    def finalize(self):
        pass

    def _copy_if_present(self, obj, data, keys=[], mapkeys={}):
        """Set obj.x from data['x'] for each x in keys if present in data.
           The dict mapkeys is handled similarly except that its keys are looked
           up in data and the corresponding value used to set obj."""
        for key in keys:
            if key in data:
                setattr(obj, key, data[key])
        for key, val in mapkeys.items():
            if key in data:
                setattr(obj, val, data[key])

    system = property(lambda self: self.sysr.system)


class _StructHandler(_Handler):
    category = '_struct'

    def __call__(self, d):
        self._copy_if_present(self.system, d, keys=('title',),
                              mapkeys={'entry_id': 'id'})


class _SoftwareHandler(_Handler):
    category = '_software'

    def __call__(self, d):
        s = self.sysr.software.get_by_id(d['pdbx_ordinal'])
        self._copy_if_present(s, d,
                keys=('name', 'classification', 'description', 'version',
                      'type', 'location'))


class _CitationHandler(_Handler):
    category = '_citation'

    def __call__(self, d):
        s = self.sysr.citations.get_by_id(d['id'])
        self._copy_if_present(s, d,
                keys=('title', 'year'),
                mapkeys={'pdbx_database_id_PubMed':'pmid',
                         'journal_abbrev':'journal',
                         'journal_volume':'volume',
                         'pdbx_database_id_DOI':'doi'})
        if 'page_first' in d:
            if 'page_last' in d:
                s.page_range = (d['page_first'], d['page_last'])
            else:
                s.page_range = d['page_first']


class _CitationAuthorHandler(_Handler):
    category = '_citation_author'

    def __call__(self, d):
        s = self.sysr.citations.get_by_id(d['citation_id'])
        if 'name' in d:
            s.authors.append(d['name'])


class _ChemCompHandler(_Handler):
    category = '_chem_comp'

    def __init__(self, *args):
        super(_ChemCompHandler, self).__init__(*args)
        # Map _chem_comp.type to corresponding subclass of ihm.ChemComp
        self.type_map = dict((x[1].type.lower(), x[1])
                             for x in inspect.getmembers(ihm, inspect.isclass)
                             if issubclass(x[1], ihm.ChemComp))

    def __call__(self, d):
        typ = d.get('type', 'other').lower()
        s = self.sysr.chem_comps.get_by_id(d['id'],
                                           self.type_map.get(typ, ihm.ChemComp))


class _EntityHandler(_Handler):
    category = '_entity'

    def __call__(self, d):
        s = self.sysr.entities.get_by_id(d['id'])
        self._copy_if_present(s, d,
                keys=('details', 'type', 'src_method', 'formula_weight'),
                mapkeys={'pdbx_description':'description',
                         'pdbx_number_of_molecules':'number_of_molecules'})


class _EntityPolySeqHandler(_Handler):
    category = '_entity_poly_seq'

    def __call__(self, d):
        s = self.sysr.entities.get_by_id(d['entity_id'])
        seq_id = int(d['num'])
        if seq_id > len(s.sequence):
            s.sequence.extend([None]*(seq_id-len(s.sequence)))
        s.sequence[seq_id-1] = self.sysr.chem_comps.get_by_id(d['mon_id'])


class _StructAsymHandler(_Handler):
    category = '_struct_asym'

    def __call__(self, d):
        s = self.sysr.asym_units.get_by_id(d['id'])
        s.entity = self.sysr.entities.get_by_id(d['entity_id'])
        self._copy_if_present(s, d, keys=('details',))


class _AssemblyDetailsHandler(_Handler):
    category = '_ihm_struct_assembly_details'

    def __call__(self, d):
        s = self.sysr.assemblies.get_by_id(d['assembly_id'])
        self._copy_if_present(s, d,
                mapkeys={'assembly_name':'name',
                         'assembly_description':'description'})


class _AssemblyHandler(_Handler):
    # todo: figure out how to populate System.complete_assembly
    category = '_ihm_struct_assembly'

    def __call__(self, d):
        a_id = d['assembly_id']
        a = self.sysr.assemblies.get_by_id(a_id)
        parent_id = d.get('parent_assembly_id', None)
        if parent_id and parent_id != a_id and not a.parent:
            a.parent = self.sysr.assemblies.get_by_id(parent_id)
        seqrng = (int(d['seq_id_begin']), int(d['seq_id_end']))
        asym_id = d.get('asym_id', None)
        if asym_id:
            asym = self.sysr.asym_units.get_by_id(asym_id)
            a.append(asym(*seqrng))
        else:
            entity = self.sysr.entities.get_by_id(d['entity_id'])
            a.append(entity(*seqrng))


class _LocalFiles(ihm.location.Repository):
    """Placeholder for files stored locally"""
    reference_provider = None
    reference_type = 'Supplementary Files'
    reference = None
    refers_to = 'Other'
    url = None


class _ExtRefHandler(_Handler):
    category = '_ihm_external_reference_info'

    def __init__(self, *args):
        super(_ExtRefHandler, self).__init__(*args)
        self.type_map = {'doi':ihm.location.Repository,
                         'supplementary files':_LocalFiles}

    def __call__(self, d):
        ref_id = d['reference_id']
        typ = d.get('reference_type', 'DOI').lower()
        repo = self.sysr.repos.get_by_id(ref_id,
                             self.type_map.get(typ, ihm.location.Repository))
        self._copy_if_present(repo, d,
                    mapkeys={'reference':'doi', 'associated_url':'url'})

    def finalize(self):
        # Map use of placeholder _LocalFiles repository to repo=None
        for location in self.system.locations:
            if hasattr(location, 'repo') \
                    and isinstance(location.repo, _LocalFiles):
                location.repo = None


class _ExtFileHandler(_Handler):
    category = '_ihm_external_files'

    def __init__(self, *args):
        super(_ExtFileHandler, self).__init__(*args)
        # Map _ihm_external_files.content_type to corresponding
        # subclass of ihm.location.FileLocation
        self.type_map = dict(
                (x[1].content_type.lower(), x[1])
                for x in inspect.getmembers(ihm.location, inspect.isclass)
                if issubclass(x[1], ihm.location.FileLocation)
                and x[1] is not ihm.location.FileLocation)

    def __call__(self, d):
        if 'content_type' in d:
            typ = d['content_type'].lower()
        else:
            typ = None
        f = self.sysr.external_files.get_by_id(d['id'],
                             self.type_map.get(typ, ihm.location.FileLocation))
        f.repo = self.sysr.repos.get_by_id(d['reference_id'])
        self._copy_if_present(f, d,
                    keys=['details'],
                    mapkeys={'file_path':'path'})
        # Handle DOI that is itself a file
        if 'file_path' not in d:
            f.path = '.'


class _DatasetListHandler(_Handler):
    category = '_ihm_dataset_list'

    def __init__(self, *args):
        super(_DatasetListHandler, self).__init__(*args)
        # Map data_type to corresponding
        # subclass of ihm.dataset.Dataset
        self.type_map = dict(
                (x[1].data_type.lower(), x[1])
                for x in inspect.getmembers(ihm.dataset, inspect.isclass)
                if issubclass(x[1], ihm.dataset.Dataset))

    def __call__(self, d):
        if 'data_type' in d:
            typ = d['data_type'].lower()
        else:
            typ = None
        f = self.sysr.datasets.get_by_id(d['id'],
                             self.type_map.get(typ, ihm.dataset.Dataset))


class _DatasetGroupHandler(_Handler):
    category = '_ihm_dataset_group'

    def __call__(self, d):
        g = self.sysr.dataset_groups.get_by_id(d['group_id'])
        ds = self.sysr.datasets.get_by_id(d['dataset_list_id'])
        g.append(ds)


class _DatasetExtRefHandler(_Handler):
    category = '_ihm_dataset_external_reference'

    def __call__(self, d):
        ds = self.sysr.datasets.get_by_id(d['dataset_list_id'])
        f = self.sysr.external_files.get_by_id(d['file_id'])
        ds.location = f


class _DatasetDBRefHandler(_Handler):
    category = '_ihm_dataset_related_db_reference'

    def __init__(self, *args):
        super(_DatasetDBRefHandler, self).__init__(*args)
        # Map data_type to corresponding
        # subclass of ihm.location.DatabaseLocation
        self.type_map = dict(
                (x[1]._db_name.lower(), x[1])
                for x in inspect.getmembers(ihm.location, inspect.isclass)
                if issubclass(x[1], ihm.location.DatabaseLocation)
                and x[1] is not ihm.location.DatabaseLocation)

    def __call__(self, d):
        ds = self.sysr.datasets.get_by_id(d['dataset_list_id'])
        if 'db_name' in d:
            typ = d['db_name'].lower()
        else:
            typ = None
        dbloc = self.sysr.db_locations.get_by_id(d['id'],
                                                 self.type_map.get(typ, None))
        ds.location = dbloc
        self._copy_if_present(dbloc, d,
                    keys=['version', 'details'],
                    mapkeys={'accession_code':'access_code'})


class _RelatedDatasetsHandler(_Handler):
    category = '_ihm_related_datasets'

    def __call__(self, d):
        derived = self.sysr.datasets.get_by_id(d['dataset_list_id_derived'])
        primary = self.sysr.datasets.get_by_id(d['dataset_list_id_primary'])
        derived.parents.append(primary)


def read(fh):
    """Read data from the mmCIF file handle `fh`.
    
       :param file fh: The file handle to read from.
       :return: A list of :class:`ihm.System` objects.
    """
    systems = []

    while True:
        s = _SystemReader()
        handlers = [_StructHandler(s), _SoftwareHandler(s), _CitationHandler(s),
                    _CitationAuthorHandler(s), _ChemCompHandler(s),
                    _EntityHandler(s), _EntityPolySeqHandler(s),
                    _StructAsymHandler(s), _AssemblyDetailsHandler(s),
                    _AssemblyHandler(s), _ExtRefHandler(s), _ExtFileHandler(s),
                    _DatasetListHandler(s), _DatasetGroupHandler(s),
                    _DatasetExtRefHandler(s), _DatasetDBRefHandler(s),
                    _RelatedDatasetsHandler(s)]
        r = ihm.format.CifReader(fh, dict((h.category, h) for h in handlers))
        more_data = r.read_file()
        for h in handlers:
            h.finalize()
        systems.append(s.system)
        if not more_data:
            break

    return systems
