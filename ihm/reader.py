"""Utility classes to read in information in mmCIF format"""

import ihm.format
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
       :param str id_attr: The attribute in the class used to store the ID.
    """
    def __init__(self, system_list, cls, id_attr, *cls_args, **cls_keys):
        self.system_list = system_list
        self._obj_by_id = {}
        self._id_attr = id_attr
        self._cls = cls
        self._cls_args = cls_args
        self._cls_keys = cls_keys

    def get_by_id(self, objid, newcls=None):
        """Get the object with given ID, creating it if it doesn't already
           exist."""
        if objid in self._obj_by_id:
            return self._obj_by_id[objid]
        else:
            if newcls is None:
                newcls = self._cls
            newobj = newcls(*self._cls_args, **self._cls_keys)
            setattr(newobj, self._id_attr, objid)
            self._obj_by_id[objid] = newobj
            if self.system_list is not None:
                self.system_list.append(newobj)
            return newobj


class _ChemCompIDMapper(_IDMapper):
    """Add extra handling to _IDMapper for the chem_comp category"""
    def __init__(self, *args, **keys):
        super(_ChemCompIDMapper, self).__init__(*args, **keys)
        # populate with standard residue types
        alphabets = [x[1] for x in inspect.getmembers(ihm, inspect.isclass)
                     if issubclass(x[1], ihm.Alphabet)
                     and x[1] is not ihm.Alphabet]
        for alphabet in alphabets:
            self._obj_by_id.update((item[1].id, item[1])
                                   for item in alphabet._comps.items())


class _SystemReader(object):
    """Track global information for a System being read from a file, such
       as the mapping from IDs to objects."""
    def __init__(self):
        self.system = ihm.System()
        self.software = _IDMapper(self.system.software, ihm.Software, '_id',
                                  *(None,)*4)
        self.citations = _IDMapper(self.system.citations, ihm.Citation, '_id',
                                   *(None,)*8)
        self.entities = _IDMapper(self.system.entities, _make_new_entity, '_id')
        self.asym_units = _IDMapper(self.system.asym_units, ihm.AsymUnit, '_id',
                                    None)
        self.chem_comps = _ChemCompIDMapper(None, ihm.ChemComp, 'id',
                                            *(None,)*3)
        self.assemblies = _IDMapper(self.system.orphan_assemblies, ihm.Assembly,
                                    '_id')


class _Handler(object):
    """Base class for all handlers of mmCIF data."""
    def __init__(self, sysr):
        self.sysr = sysr

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


def read(fh):
    """Read data from the mmCIF file handle `fh`.
    
       :param file fh: The file handle to read from.
       :return: A list of :class:`ihm.System` objects.
    """
    systems = []

    s = _SystemReader()
    handlers = [_StructHandler(s), _SoftwareHandler(s), _CitationHandler(s),
                _CitationAuthorHandler(s), _ChemCompHandler(s),
                _EntityHandler(s), _EntityPolySeqHandler(s),
                _StructAsymHandler(s), _AssemblyDetailsHandler(s),
                _AssemblyHandler(s)]
    r = ihm.format.CifReader(fh, dict((h.category, h) for h in handlers))
    r.read_file()

    # todo: handle multiple systems (from multiple data blocks)
    systems.append(s.system)
    return systems
