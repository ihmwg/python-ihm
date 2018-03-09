import utils
import os
import unittest
import sys
if sys.version_info[0] >= 3:
    from io import StringIO
else:
    from io import BytesIO as StringIO

TOPDIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
utils.set_search_paths(TOPDIR)
import ihm.dumper
import ihm.format
import ihm.location
import ihm.representation
import ihm.startmodel

def _get_dumper_output(dumper, system):
    fh = StringIO()
    writer = ihm.format.CifWriter(fh)
    dumper.dump(system, writer)
    return fh.getvalue()

class Tests(unittest.TestCase):
    def test_write(self):
        """Test write() function"""
        sys1 = ihm.System('system1')
        sys2 = ihm.System('system 2+3')
        fh = StringIO()
        ihm.dumper.write(fh, [sys1, sys2])
        lines = fh.getvalue().split('\n')
        self.assertEqual(lines[:2], ["data_system1", "_entry.id system1"])
        self.assertEqual(lines[9:11],
                         ["data_system23", "_entry.id 'system 2+3'"])

    def test_dumper(self):
        """Test Dumper base class"""
        dumper = ihm.dumper._Dumper()
        dumper.finalize(None)
        dumper.dump(None, None)

    def test_entry_dumper(self):
        """Test EntryDumper"""
        system = ihm.System(name='test_model')
        dumper = ihm.dumper._EntryDumper()
        out = _get_dumper_output(dumper, system)
        self.assertEqual(out, "data_test_model\n_entry.id test_model\n")

    def test_software(self):
        """Test SoftwareDumper"""
        system = ihm.System()
        system.software.append(ihm.Software(
                         name='test', classification='test code',
                         description='Some test program',
                         version=1, location='http://test.org'))
        system.software.append(ihm.Software(
                          name='foo', classification='test code',
                          description='Other test program',
                          location='http://test2.org'))
        dumper = ihm.dumper._SoftwareDumper()
        out = _get_dumper_output(dumper, system)
        self.assertEqual(out, """#
loop_
_software.pdbx_ordinal
_software.name
_software.classification
_software.description
_software.version
_software.type
_software.location
1 test 'test code' 'Some test program' 1 program http://test.org
2 foo 'test code' 'Other test program' . program http://test2.org
#
""")

    def test_entity_dumper(self):
        """Test EntityDumper"""
        system = ihm.System()
        system.entities.append(ihm.Entity('ABC', description='foo'))
        system.entities.append(ihm.Entity('ABCD', description='baz'))
        dumper = ihm.dumper._EntityDumper()
        dumper.finalize(system) # Assign IDs
        out = _get_dumper_output(dumper, system)
        self.assertEqual(out, """#
loop_
_entity.id
_entity.type
_entity.src_method
_entity.pdbx_description
_entity.formula_weight
_entity.pdbx_number_of_molecules
_entity.details
1 polymer man foo ? 1 .
2 polymer man baz ? 1 .
#
""")

    def test_entity_duplicates(self):
        """Test EntityDumper with duplicate entities"""
        system = ihm.System()
        system.entities.append(ihm.Entity('ABC'))
        system.entities.append(ihm.Entity('ABC'))
        dumper = ihm.dumper._EntityDumper()
        self.assertRaises(ValueError, dumper.finalize, system)

    def test_chem_comp_dumper(self):
        """Test ChemCompDumper"""
        system = ihm.System()
        system.entities.append(ihm.Entity('ACGTTA'))
        dumper = ihm.dumper._ChemCompDumper()
        out = _get_dumper_output(dumper, system)
        self.assertEqual(out, """#
loop_
_chem_comp.id
_chem_comp.type
ALA 'L-peptide linking'
CYS 'L-peptide linking'
GLY 'L-peptide linking'
THR 'L-peptide linking'
#
""")

    def test_entity_poly_dumper(self):
        """Test EntityPolyDumper"""
        system = ihm.System()
        e1 = ihm.Entity('ACGT')
        e2 = ihm.Entity('ACC')
        system.entities.extend((e1, e2))
        # One entity is modeled (with an asym unit) the other not; this should
        # be reflected in pdbx_strand_id
        system.asym_units.append(ihm.AsymUnit(e1, 'foo'))
        system.asym_units.append(ihm.AsymUnit(e1, 'bar'))
        ed = ihm.dumper._EntityDumper()
        ed.finalize(system) # Assign entity IDs
        sd = ihm.dumper._StructAsymDumper()
        sd.finalize(system) # Assign asym IDs
        dumper = ihm.dumper._EntityPolyDumper()
        out = _get_dumper_output(dumper, system)
        self.assertEqual(out, """#
loop_
_entity_poly.entity_id
_entity_poly.type
_entity_poly.nstd_linkage
_entity_poly.nstd_monomer
_entity_poly.pdbx_strand_id
_entity_poly.pdbx_seq_one_letter_code
_entity_poly.pdbx_seq_one_letter_code_can
1 polypeptide(L) no no A ACGT ACGT
2 polypeptide(L) no no . ACC ACC
#
""")

    def test_entity_poly_seq_dumper(self):
        """Test EntityPolySeqDumper"""
        system = ihm.System()
        system.entities.append(ihm.Entity('ACGT'))
        system.entities.append(ihm.Entity('ACC'))
        ed = ihm.dumper._EntityDumper()
        ed.finalize(system) # Assign IDs
        dumper = ihm.dumper._EntityPolySeqDumper()
        out = _get_dumper_output(dumper, system)
        self.assertEqual(out, """#
loop_
_entity_poly_seq.entity_id
_entity_poly_seq.num
_entity_poly_seq.mon_id
_entity_poly_seq.hetero
1 1 ALA .
1 2 CYS .
1 3 GLY .
1 4 THR .
2 1 ALA .
2 2 CYS .
2 3 CYS .
#
""")

    def test_struct_asym_dumper(self):
        """Test StructAsymDumper"""
        system = ihm.System()
        e1 = ihm.Entity('ACGT')
        e2 = ihm.Entity('ACC')
        e1._id = 1
        e2._id = 2
        system.entities.extend((e1, e2))
        system.asym_units.append(ihm.AsymUnit(e1, 'foo'))
        system.asym_units.append(ihm.AsymUnit(e1, 'bar'))
        system.asym_units.append(ihm.AsymUnit(e2, 'baz'))
        dumper = ihm.dumper._StructAsymDumper()
        dumper.finalize(system) # assign IDs
        out = _get_dumper_output(dumper, system)
        self.assertEqual(out, """#
loop_
_struct_asym.id
_struct_asym.entity_id
_struct_asym.details
A 1 foo
B 1 bar
C 2 baz
#
""")

    def test_assembly_all_modeled(self):
        """Test AssemblyDumper, all components modeled"""
        system = ihm.System()
        e1 = ihm.Entity('AAA', description='foo')
        e2 = ihm.Entity('AA', description='baz')
        a1 = ihm.AsymUnit(e1)
        a2 = ihm.AsymUnit(e1)
        a3 = ihm.AsymUnit(e2)
        system.entities.extend((e1, e2))
        system.asym_units.extend((a1, a2, a3))

        c = ihm.AssemblyComponent(a2, seq_id_range=(2,3))
        system.assemblies.append(ihm.Assembly((a1, c), name='foo'))
        # Out of order assembly (should be ordered on output)
        system.assemblies.append(ihm.Assembly((a3, a2), name='bar'))
        # Duplicate assembly (should be ignored)
        system.assemblies.append(ihm.Assembly((a2, a3)))

        # Assign entity and asym IDs
        ihm.dumper._EntityDumper().finalize(system)
        ihm.dumper._StructAsymDumper().finalize(system)

        d = ihm.dumper._AssemblyDumper()
        d.finalize(system)
        self.assertEqual([a._id for a in system.assemblies], [1,2,3,3])
        out = _get_dumper_output(d, system)
        self.assertEqual(out, """#
loop_
_ihm_struct_assembly_details.assembly_id
_ihm_struct_assembly_details.assembly_name
_ihm_struct_assembly_details.assembly_description
1 'Complete assembly' 'All known components'
2 foo .
3 bar .
#
#
loop_
_ihm_struct_assembly.ordinal_id
_ihm_struct_assembly.assembly_id
_ihm_struct_assembly.parent_assembly_id
_ihm_struct_assembly.entity_description
_ihm_struct_assembly.entity_id
_ihm_struct_assembly.asym_id
_ihm_struct_assembly.seq_id_begin
_ihm_struct_assembly.seq_id_end
1 1 1 foo 1 A 1 3
2 1 1 foo 1 B 1 3
3 1 1 baz 2 C 1 2
4 2 2 foo 1 A 1 3
5 2 2 foo 1 B 2 3
6 3 3 foo 1 B 1 3
7 3 3 baz 2 C 1 2
#
""")

    def test_assembly_subset_modeled(self):
        """Test AssemblyDumper, subset of components modeled"""
        system = ihm.System()
        e1 = ihm.Entity('AAA', description='foo')
        e2 = ihm.Entity('AA', description='bar')
        a1 = ihm.AsymUnit(e1)
        system.entities.extend((e1, e2))
        system.asym_units.append(a1)
        # Note that no asym unit uses entity e2, so the assembly
        # should omit the chain ID ('.')

        # Assign entity and asym IDs
        ihm.dumper._EntityDumper().finalize(system)
        ihm.dumper._StructAsymDumper().finalize(system)

        d = ihm.dumper._AssemblyDumper()
        d.finalize(system)
        out = _get_dumper_output(d, system)
        self.assertEqual(out, """#
loop_
_ihm_struct_assembly_details.assembly_id
_ihm_struct_assembly_details.assembly_name
_ihm_struct_assembly_details.assembly_description
1 'Complete assembly' 'All known components'
#
#
loop_
_ihm_struct_assembly.ordinal_id
_ihm_struct_assembly.assembly_id
_ihm_struct_assembly.parent_assembly_id
_ihm_struct_assembly.entity_description
_ihm_struct_assembly.entity_id
_ihm_struct_assembly.asym_id
_ihm_struct_assembly.seq_id_begin
_ihm_struct_assembly.seq_id_end
1 1 1 foo 1 A 1 3
2 1 1 bar 2 . 1 2
#
""")

    def test_external_reference_dumper(self):
        """Test ExternalReferenceDumper"""
        system = ihm.System()
        repo1 = ihm.location.Repository(doi="foo")
        repo2 = ihm.location.Repository(doi="10.5281/zenodo.46266",
                                        url='nup84-v1.0.zip',
                                        top_directory=os.path.join('foo',
                                                                   'bar'))
        repo3 = ihm.location.Repository(doi="10.5281/zenodo.58025",
                                        url='foo.spd')
        l = ihm.location.InputFileLocation(repo=repo1, path='bar')
        system.locations.append(l)
        # Duplicates should be ignored
        l = ihm.location.InputFileLocation(repo=repo1, path='bar')
        system.locations.append(l)
        # Different file, same repository
        l = ihm.location.InputFileLocation(repo=repo1, path='baz')
        system.locations.append(l)
        # Different repository
        l = ihm.location.OutputFileLocation(repo=repo2, path='baz')
        system.locations.append(l)
        # Repository containing a single file (not an archive)
        l = ihm.location.InputFileLocation(repo=repo3, path='foo.spd',
                                           details='EM micrographs')
        system.locations.append(l)

        with utils.temporary_directory('') as tmpdir:
            bar = os.path.join(tmpdir, 'test_mmcif_extref.tmp')
            with open(bar, 'w') as f:
                f.write("abcd")
            # Local file
            system.locations.append(ihm.location.WorkflowFileLocation(bar))
            # DatabaseLocations should be ignored
            system.locations.append(ihm.location.PDBLocation(
                                              '1abc', '1.0', 'test details'))

            d = ihm.dumper._ExternalReferenceDumper()
            d.finalize(system)
            out = _get_dumper_output(d, system)
            self.assertEqual(out, """#
loop_
_ihm_external_reference_info.reference_id
_ihm_external_reference_info.reference_provider
_ihm_external_reference_info.reference_type
_ihm_external_reference_info.reference
_ihm_external_reference_info.refers_to
_ihm_external_reference_info.associated_url
1 . DOI foo Other .
2 Zenodo DOI 10.5281/zenodo.46266 Archive nup84-v1.0.zip
3 Zenodo DOI 10.5281/zenodo.58025 File foo.spd
4 . 'Supplementary Files' . Other .
#
#
loop_
_ihm_external_files.id
_ihm_external_files.reference_id
_ihm_external_files.file_path
_ihm_external_files.content_type
_ihm_external_files.file_size_bytes
_ihm_external_files.details
1 1 bar 'Input data or restraints' . .
2 1 baz 'Input data or restraints' . .
3 2 foo/bar/baz 'Modeling or post-processing output' . .
4 3 foo.spd 'Input data or restraints' . 'EM micrographs'
5 4 %s 'Modeling workflow or script' 4 .
#
""" % bar.replace(os.sep, '/'))

    def test_dataset_dumper_duplicates_details(self):
        """DatasetDumper ignores duplicate datasets with differing details"""
        system = ihm.System()
        dump = ihm.dumper._DatasetDumper()
        l = ihm.location.PDBLocation('1abc', '1.0', 'test details')
        ds1 = ihm.dataset.PDBDataset(l)
        system.datasets.append(ds1)
        # A duplicate dataset should be ignored even if details differ
        l = ihm.location.PDBLocation('1abc', '1.0', 'other details')
        ds2 = ihm.dataset.PDBDataset(l)
        system.datasets.append(ds2)
        dump.finalize(system) # Assign IDs
        self.assertEqual(ds1._id, 1)
        self.assertEqual(ds2._id, 1)
        self.assertEqual(len(dump._dataset_by_id), 1)

    def test_dataset_dumper_duplicates_samedata_sameloc(self):
        """DatasetDumper doesn't duplicate same datasets in same location"""
        system = ihm.System()
        loc1 = ihm.location.DatabaseLocation("mydb", "abc", "1.0", "")
        loc2 = ihm.location.DatabaseLocation("mydb", "xyz", "1.0", "")

        # Identical datasets in the same location aren't duplicated
        cx1 = ihm.dataset.CXMSDataset(loc1)
        cx2 = ihm.dataset.CXMSDataset(loc1)

        dump = ihm.dumper._DatasetDumper()
        system.datasets.extend((cx1, cx2))
        dump.finalize(system) # Assign IDs
        self.assertEqual(cx1._id, 1)
        self.assertEqual(cx2._id, 1)
        self.assertEqual(len(dump._dataset_by_id), 1)

    def test_dataset_dumper_duplicates_samedata_diffloc(self):
        """DatasetDumper is OK with same datasets in different locations"""
        system = ihm.System()
        loc1 = ihm.location.DatabaseLocation("mydb", "abc", "1.0", "")
        loc2 = ihm.location.DatabaseLocation("mydb", "xyz", "1.0", "")
        cx1 = ihm.dataset.CXMSDataset(loc1)
        cx2 = ihm.dataset.CXMSDataset(loc2)
        dump = ihm.dumper._DatasetDumper()
        system.datasets.extend((cx1, cx2))
        dump.finalize(system) # Assign IDs
        self.assertEqual(cx1._id, 1)
        self.assertEqual(cx2._id, 2)
        self.assertEqual(len(dump._dataset_by_id), 2)

    def test_dataset_dumper_duplicates_diffdata_sameloc(self):
        """DatasetDumper is OK with different datasets in same location"""
        system = ihm.System()
        # Different datasets in same location are OK (but odd)
        loc2 = ihm.location.DatabaseLocation("mydb", "xyz", "1.0", "")
        cx2 = ihm.dataset.CXMSDataset(loc2)
        em3d = ihm.dataset.EMDensityDataset(loc2)
        dump = ihm.dumper._DatasetDumper()
        system.datasets.extend((cx2, em3d))
        dump.finalize(system) # Assign IDs
        self.assertEqual(cx2._id, 1)
        self.assertEqual(em3d._id, 2)
        self.assertEqual(len(dump._dataset_by_id), 2)

    def test_dataset_dumper_allow_duplicates(self):
        """DatasetDumper is OK with duplicates if allow_duplicates=True"""
        system = ihm.System()
        emloc1 = ihm.location.EMDBLocation("abc")
        emloc2 = ihm.location.EMDBLocation("abc")
        emloc1._allow_duplicates = True
        em3d_1 = ihm.dataset.EMDensityDataset(emloc1)
        em3d_2 = ihm.dataset.EMDensityDataset(emloc2)
        dump = ihm.dumper._DatasetDumper()
        system.datasets.extend((em3d_1, em3d_2))
        dump.finalize(system) # Assign IDs
        self.assertEqual(em3d_1._id, 1)
        self.assertEqual(em3d_2._id, 2)
        self.assertEqual(len(dump._dataset_by_id), 2)

    def test_dataset_dumper_dump(self):
        """Test DatasetDumper.dump()"""
        system = ihm.System()
        l = ihm.location.InputFileLocation(repo='foo', path='bar')
        l._id = 97
        ds1 = ihm.dataset.CXMSDataset(l)
        system.datasets.append(ds1)

        l = ihm.location.PDBLocation('1abc', '1.0', 'test details')
        ds2 = ihm.dataset.PDBDataset(l)
        system.datasets.append(ds2)
        ds2.add_parent(ds1)

        d = ihm.dumper._DatasetDumper()
        d.finalize(system) # Assign IDs
        out = _get_dumper_output(d, system)
        self.assertEqual(out, """#
loop_
_ihm_dataset_list.id
_ihm_dataset_list.data_type
_ihm_dataset_list.database_hosted
1 'CX-MS data' NO
2 'Experimental model' YES
#
#
loop_
_ihm_dataset_external_reference.id
_ihm_dataset_external_reference.dataset_list_id
_ihm_dataset_external_reference.file_id
1 1 97
#
#
loop_
_ihm_dataset_related_db_reference.id
_ihm_dataset_related_db_reference.dataset_list_id
_ihm_dataset_related_db_reference.db_name
_ihm_dataset_related_db_reference.accession_code
_ihm_dataset_related_db_reference.version
_ihm_dataset_related_db_reference.details
1 2 PDB 1abc 1.0 'test details'
#
#
loop_
_ihm_related_datasets.ordinal_id
_ihm_related_datasets.dataset_list_id_derived
_ihm_related_datasets.dataset_list_id_primary
1 2 1
#
""")


    def test_model_representation_dump(self):
        """Test ModelRepresentationDumper"""
        system = ihm.System()
        e1 = ihm.Entity('AAAAAAAA', description='bar')
        system.entities.append(e1)
        asym = ihm.AsymUnit(e1, 'foo')
        system.asym_units.append(asym)

        s1 = ihm.representation.AtomicSegment(
                    asym(1,2), starting_model=None, rigid=True)
        s2 = ihm.representation.ResidueSegment(
                    asym(3,4), starting_model=None,
                    rigid=False, primitive='sphere')
        s3 = ihm.representation.MultiResidueSegment(
                    asym(1,2), starting_model=None,
                    rigid=False, primitive='gaussian')
        s4 = ihm.representation.FeatureSegment(
                    asym(3,4), starting_model=None,
                    rigid=True, primitive='other', count=3)
        r1 = ihm.representation.Representation((s1, s2))
        r2 = ihm.representation.Representation((s3, s4))
        system.representations.extend((r1, r2))

        e1._id = 42
        asym._id = 'X'

        dumper = ihm.dumper._ModelRepresentationDumper()
        dumper.finalize(system) # assign IDs
        out = _get_dumper_output(dumper, system)
        self.assertEqual(out, """#
loop_
_ihm_model_representation.ordinal_id
_ihm_model_representation.representation_id
_ihm_model_representation.segment_id
_ihm_model_representation.entity_id
_ihm_model_representation.entity_description
_ihm_model_representation.entity_asym_id
_ihm_model_representation.seq_id_begin
_ihm_model_representation.seq_id_end
_ihm_model_representation.model_object_primitive
_ihm_model_representation.starting_model_id
_ihm_model_representation.model_mode
_ihm_model_representation.model_granularity
_ihm_model_representation.model_object_count
1 1 1 42 bar X 1 2 atomistic . rigid by-atom .
2 1 2 42 bar X 3 4 sphere . flexible by-residue .
3 2 1 42 bar X 1 2 gaussian . flexible multi-residue .
4 2 2 42 bar X 3 4 other . rigid by-feature 3
#
""")

    def test_starting_model_dumper(self):
        """Test StartingModelDumper"""
        system = ihm.System()
        e1 = ihm.Entity('AAA', description='foo')
        system.entities.append(e1)
        asym = ihm.AsymUnit(e1, 'bar')
        system.asym_units.append(asym)
        l = ihm.location.PDBLocation('1abc', '1.0', 'test details')
        ds1 = ihm.dataset.PDBDataset(l)
        system.datasets.append(ds1)

        s1 = ihm.startmodel.PDBSource('1abc', 'C', [])
        sm = ihm.startmodel.StartingModel(asym, ds1, 'A', [s1], offset=10)
        system.starting_models.append(sm)

        e1._id = 42
        asym._id = 99
        ds1._id = 101
        dumper = ihm.dumper._StartingModelDumper()
        dumper.finalize(system) # assign IDs
        out = _get_dumper_output(dumper, system)
        self.assertEqual(out, """#
loop_
_ihm_starting_model_details.starting_model_id
_ihm_starting_model_details.entity_id
_ihm_starting_model_details.entity_description
_ihm_starting_model_details.asym_id
_ihm_starting_model_details.seq_id_begin
_ihm_starting_model_details.seq_id_end
_ihm_starting_model_details.starting_model_source
_ihm_starting_model_details.starting_model_auth_asym_id
_ihm_starting_model_details.starting_model_sequence_offset
_ihm_starting_model_details.dataset_list_id
1 42 foo 99 1 3 'experimental model' A 10 101
#
""")



if __name__ == '__main__':
    unittest.main()
