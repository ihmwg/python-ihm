import utils
import os
import unittest

TOPDIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
utils.set_search_paths(TOPDIR)
import ihm.multi_state_scheme


class Tests(unittest.TestCase):

    def test_multistatescheme_init(self):
        """Test the initialization of MultiStateScheme"""
        class MockObject(object):
            pass
        mssc1 = ihm.multi_state_scheme.Connectivity(
            begin_state='s1',
            end_state='s2')
        mss1 = ihm.multi_state_scheme.MultiStateScheme(
            name='n',
            details='d',
            connectivities=[mssc1],
            relaxation_times=['lr'])
        self.assertEqual(mss1.name, 'n')
        self.assertEqual(mss1.details, 'd')
        self.assertEqual(mss1._connectivity_list, [mssc1])
        self.assertEqual(mss1._relaxation_time_list, ['lr'])
        self.assertEqual(mss1._states, ['s1', 's2'])

        mss2 = ihm.multi_state_scheme.MultiStateScheme(
            name='n2',
            details='d2',
            connectivities=[],
            relaxation_times=[])
        self.assertEqual(len(mss2._connectivity_list), 0)
        self.assertEqual(len(mss2._relaxation_time_list), 0)

        mss3 = ihm.multi_state_scheme.MultiStateScheme(
            name='n3',
            details='d3',
            connectivities=[mssc1, mssc1],
            relaxation_times=['lr', 'lr']
        )
        self.assertEqual(mss3._connectivity_list, [mssc1])
        self.assertEqual(mss3._relaxation_time_list, ['lr'])

    def test_multistatescheme_add_connectivity(self):
        """Test addition of a connectivity to a MultiStateScheme"""
        class MockObject(object):
            pass
        mss1 = ihm.multi_state_scheme.MultiStateScheme(name='n',
                                                       details='d')
        # The connectivity_list should be empty upon initialization
        self.assertEqual(len(mss1._connectivity_list), 0)
        # Add a connectivity should add it to the connectivity_list and the
        # states should be stored as well
        mssc1 = ihm.multi_state_scheme.Connectivity(
            begin_state='s1',
            end_state='s2')
        mss1.add_connectivity(mssc1)
        self.assertEqual(len(mss1._connectivity_list), 1)
        self.assertEqual(mss1._connectivity_list, [mssc1])
        self.assertEqual(mss1._states, ['s1', 's2'])
        # add a connectivity without end_state
        mssc2 = ihm.multi_state_scheme.Connectivity(
            begin_state='s3')
        mss1.add_connectivity(mssc2)
        self.assertEqual(len(mss1._connectivity_list), 2)
        self.assertEqual(mss1._connectivity_list, [mssc1,
                                                   mssc2])
        self.assertEqual(mss1._states, ['s1', 's2', 's3'])
        # add a connectivity with a previously known state should not add it
        # to the states
        mssc3 = ihm.multi_state_scheme.Connectivity(
            begin_state='s2',
            end_state='s4')
        mss1.add_connectivity(mssc3)
        self.assertEqual(len(mss1._connectivity_list), 3)
        self.assertEqual(mss1._connectivity_list, [mssc1, mssc2, mssc3])
        self.assertEqual(mss1._states, ['s1', 's2', 's3', 's4'])

    def test_multistatescheme_add_relaxation_time(self):
        """Test addition of a relaxation time to a MultiStateScheme"""
        mss1 = ihm.multi_state_scheme.MultiStateScheme(name='n')
        # The relaxation_time_list should be empty upon initialization
        self.assertEqual(len(mss1._relaxation_time_list), 0)
        # Add a relaxation time
        mss1.add_relaxation_time('r')
        self.assertEqual(mss1._relaxation_time_list, ['r'])

    def test_multistatesscheme_get_connectivities(self):
        """Test the return of connectivities from a MultiStateScheme"""
        mssc1 = ihm.multi_state_scheme.Connectivity(
            begin_state='s1',
            end_state='s2')
        mssc2 = ihm.multi_state_scheme.Connectivity(
            begin_state='s2',
            end_state='s3')
        mssc3 = ihm.multi_state_scheme.Connectivity(
            begin_state='s2',
            end_state='s4')
        mss1 = ihm.multi_state_scheme.MultiStateScheme(
            name='n',
            connectivities=[mssc1, mssc2])
        self.assertEqual(mss1.get_connectivities(), [mssc1, mssc2])
        mss1.add_connectivity(mssc3)
        # Test addition of the same connectivity multiple times
        self.assertEqual(mss1.get_connectivities(), [mssc1, mssc2, mssc3])
        mss1.add_connectivity(mssc3)
        self.assertEqual(mss1.get_connectivities(), [mssc1, mssc2, mssc3])
        mss1.add_connectivity(mssc1)
        self.assertEqual(mss1.get_connectivities(), [mssc1, mssc2, mssc3])

    def test_multistatescheme_get_relaxation_times(self):
        """Test the return of relaxation times from a MultiStateScheme"""
        mss1 = ihm.multi_state_scheme.MultiStateScheme(
            name='n',
            relaxation_times=['r1', 'r2']
        )
        self.assertEqual(mss1.get_relaxation_times(), ['r1', 'r2'])
        mss1.add_relaxation_time('r3')
        self.assertEqual(mss1.get_relaxation_times(), ['r1', 'r2', 'r3'])
        mss1.add_relaxation_time('r3')
        self.assertEqual(mss1.get_relaxation_times(), ['r1', 'r2', 'r3', 'r3'])

    def test_multistatescheme_get_states(self):
        """Test the return of states from a MultiStateScheme"""
        mssc1 = ihm.multi_state_scheme.Connectivity(
            begin_state='s1',
            end_state='s2')
        mssc2 = ihm.multi_state_scheme.Connectivity(
            begin_state='s1')
        mssc3 = ihm.multi_state_scheme.Connectivity(
            begin_state='s2',
            end_state='s3')

        mss1 = ihm.multi_state_scheme.MultiStateScheme(
            name='n',
            connectivities=[mssc1])
        self.assertEqual(mss1.get_states(), ['s1', 's2'])
        mss1.add_connectivity(mssc2)
        self.assertEqual(mss1.get_states(), ['s1', 's2'])
        mss1.add_connectivity(mssc3)
        self.assertEqual(mss1.get_states(), ['s1', 's2', 's3'])

    def test_multistatescheme_eq(self):
        """Test equality of MultiStateScheme objects"""
        class MockObject(object):
            pass
        mssc1 = ihm.multi_state_scheme.Connectivity(
            begin_state='s1')
        mssc2 = ihm.multi_state_scheme.Connectivity(
            begin_state='s2')
        mssc3 = ihm.multi_state_scheme.Connectivity(
            begin_state='s3')
        mssc4 = ihm.multi_state_scheme.Connectivity(
            begin_state='s1',
            end_state='s4')

        mss_ref = ihm.multi_state_scheme.MultiStateScheme(
            name='name1',
            details='details1',
            connectivities=[mssc1])
        mss_equal = ihm.multi_state_scheme.MultiStateScheme(
            name='name1',
            details='details1',
            connectivities=[mssc1])
        mss_unequal = ihm.multi_state_scheme.MultiStateScheme(
            name='name2',
            details='details2',
            connectivities=[mssc2])
        mss_unequal2 = ihm.multi_state_scheme.MultiStateScheme(
            name='name1',
            details='details1',
            connectivities=[mssc3])
        mss_unequal4 = ihm.multi_state_scheme.MultiStateScheme(
            name='name1',
            details='details1',
            connectivities=[mssc4])
        mss_unequal5 = ihm.multi_state_scheme.MultiStateScheme(
            name='name1',
            details='details1',
            connectivities=[mssc1],
            relaxation_times=['r1'])

        self.assertTrue(mss_ref == mss_equal)
        self.assertFalse(mss_ref == mss_unequal)
        self.assertTrue(mss_ref != mss_unequal)
        self.assertFalse(mss_ref == mss_unequal2)
        self.assertTrue(mss_ref != mss_unequal2)
        self.assertFalse(mss_ref == mss_unequal4)
        self.assertTrue(mss_ref != mss_unequal4)
        self.assertFalse(mss_ref == mss_unequal5)
        self.assertTrue(mss_ref != mss_unequal5)

    def test_multistateschemeconnectivity_init(self):
        """Test initialization of Connectivity"""
        mssc1 = ihm.multi_state_scheme.Connectivity(
            begin_state='s1',
            end_state='s2',
            details='details1',
            dataset_group='dataset_group1',
            kinetic_rate='kinetic_rate1',
            relaxation_time='relaxation_time1')
        self.assertEqual(mssc1.begin_state, 's1')
        self.assertEqual(mssc1.end_state, 's2')
        self.assertEqual(mssc1.details, 'details1')
        self.assertEqual(mssc1.dataset_group, 'dataset_group1')
        self.assertEqual(mssc1.kinetic_rate, 'kinetic_rate1')
        self.assertEqual(mssc1.relaxation_time, 'relaxation_time1')

    def test_multistateschemeconnectivity_eq(self):
        """Test equality of Connectivity objects"""
        mssc_ref = ihm.multi_state_scheme.Connectivity(
            begin_state='s1',
            end_state='s2',
            details='details1',
            dataset_group='dataset_group1',
            kinetic_rate='kinetic_rate1',
            relaxation_time='relaxation_time1')

        mssc_equal = ihm.multi_state_scheme.Connectivity(
            begin_state='s1',
            end_state='s2',
            details='details1',
            dataset_group='dataset_group1',
            kinetic_rate='kinetic_rate1',
            relaxation_time='relaxation_time1')

        mssc_unequal1 = ihm.multi_state_scheme.Connectivity(
            begin_state='s1',
            end_state='s3',
            details='details1',
            dataset_group='dataset_group1',
            kinetic_rate='kinetic_rate1',
            relaxation_time='relaxation_time1')

        mssc_unequal2 = ihm.multi_state_scheme.Connectivity(
            begin_state='s1',
            details='details1',
            dataset_group='dataset_group1',
            kinetic_rate='kinetic_rate1',
            relaxation_time='relaxation_time1')

        self.assertTrue(mssc_ref == mssc_equal)
        self.assertFalse(mssc_ref == mssc_unequal1)
        self.assertTrue(mssc_ref != mssc_unequal1)
        self.assertFalse(mssc_ref == mssc_unequal2)
        self.assertTrue(mssc_ref != mssc_unequal2)

    def test_kineticrate_init(self):
        """Test initialization of KineticRate"""
        # Initialization with only transition_rate_constant given
        k1 = ihm.multi_state_scheme.KineticRate(transition_rate_constant=1.0)
        self.assertEqual(k1.transition_rate_constant, 1.0)
        # Initialization with equilibrium_constant
        k2 = ihm.multi_state_scheme.KineticRate(
            equilibrium_constant=1.0,
            equilibrium_constant_unit="unit",
            equilibrium_constant_determination_method='equilibrium constant '
                                                      'is determined from '
                                                      'population')
        self.assertEqual(k2.equilibrium_constant, 1.0)
        self.assertEqual(k2.equilibrium_constant_unit, "unit")
        self.assertEqual(
            k2.equilibrium_constant_determination_method, 'equilibrium '
                                                          'constant is '
                                                          'determined from '
                                                          'population')
        # Initialization with all values given
        k3 = ihm.multi_state_scheme.KineticRate(
            transition_rate_constant=0.5,
            equilibrium_constant=1.0,
            equilibrium_constant_unit="unit",
            equilibrium_constant_determination_method='equilibrium constant '
                                                      'is determined from '
                                                      'population',
            details="details1",
            dataset_group='dataset_group1',
            file='file1')
        self.assertEqual(k3.transition_rate_constant, 0.5)
        self.assertEqual(k3.equilibrium_constant, 1.0)
        self.assertEqual(k3.equilibrium_constant_unit, "unit")
        self.assertEqual(k3.equilibrium_constant_determination_method,
                         'equilibrium constant is determined from population')
        self.assertEqual(k3.details, "details1")
        self.assertEqual(k3.dataset_group, 'dataset_group1')
        self.assertEqual(k3.external_file, 'file1')

        # Initialization with wrong equilibrium_constant_determination_method
        # raises ValueError
        self.assertRaises(
            ValueError,
            ihm.multi_state_scheme.KineticRate,
            equilibrium_constant=2.0,
            equilibrium_constant_determination_method='wrong_method'
        )

    def test_kineticrate_eq(self):
        """Test equality of KineticRate objects"""
        k_ref = ihm.multi_state_scheme.KineticRate(
            transition_rate_constant=1.0,
            equilibrium_constant=1.5,
            equilibrium_constant_determination_method='equilibrium constant '
                                                      'is determined from '
                                                      'population',
            equilibrium_constant_unit="unit1",
            details="details1",
            dataset_group="dataset_group1",
            file="file1"
        )
        k_equal = ihm.multi_state_scheme.KineticRate(
            transition_rate_constant=1.0,
            equilibrium_constant=1.5,
            equilibrium_constant_determination_method='equilibrium constant '
                                                      'is determined from '
                                                      'population',
            equilibrium_constant_unit="unit1",
            details="details1",
            dataset_group="dataset_group1",
            file="file1"
        )
        k_unequal1 = ihm.multi_state_scheme.KineticRate(
            transition_rate_constant=2.0,
            equilibrium_constant=1.5,
            equilibrium_constant_determination_method='equilibrium constant '
                                                      'is determined from '
                                                      'population',
            equilibrium_constant_unit="unit1",
            details="details1",
            dataset_group="dataset_group1",
            file="file1"
        )
        k_unequal2 = ihm.multi_state_scheme.KineticRate(
            transition_rate_constant=1.0,
            equilibrium_constant=1.5,
            equilibrium_constant_determination_method='equilibrium constant '
                                                      'is determined from '
                                                      'kinetic rates, kAB/kBA',
            equilibrium_constant_unit="unit1",
            details="details1",
            dataset_group="dataset_group1",
            file="file1"
        )
        k_unequal3 = ihm.multi_state_scheme.KineticRate(
            transition_rate_constant=1.0,
            details="details1",
            dataset_group="dataset_group1",
            file="file1"
        )
        self.assertTrue(k_ref == k_equal)
        self.assertFalse(k_ref == k_unequal1)
        self.assertTrue(k_ref != k_unequal1)
        self.assertFalse(k_ref == k_unequal2)
        self.assertTrue(k_ref != k_unequal2)
        self.assertFalse(k_ref == k_unequal3)
        self.assertTrue(k_ref != k_unequal3)

    def test_relaxationtime_init(self):
        """Test initialization of RelaxationTime"""
        r1 = ihm.multi_state_scheme.RelaxationTime(
            value=1.0,
            unit='milliseconds',
            details='details1',
            dataset_group='dataset_group1',
            file='file1'
        )
        self.assertEqual(r1.value, 1.0)
        self.assertEqual(r1.unit, 'milliseconds')
        self.assertEqual(r1.details, 'details1')
        self.assertEqual(r1.dataset_group, 'dataset_group1')
        self.assertEqual(r1.external_file, 'file1')
        # Check whether a wrong unit raises a ValueError
        self.assertRaises(
            ValueError,
            ihm.multi_state_scheme.RelaxationTime,
            value=2.0,
            unit='wrong_unit')

    def test_relaxationtime_eq(self):
        """Test equality of RelaxationTime objetcs"""
        r_ref = ihm.multi_state_scheme.RelaxationTime(
            value=1.0,
            unit='milliseconds',
            details='details1',
            dataset_group='dataset_group1',
            file='file1'
        )
        r_equal = ihm.multi_state_scheme.RelaxationTime(
            value=1.0,
            unit='milliseconds',
            details='details1',
            dataset_group='dataset_group1',
            file='file1'
        )
        r_unequal1 = ihm.multi_state_scheme.RelaxationTime(
            value=2.0,
            unit='milliseconds',
            details='details1',
            dataset_group='dataset_group1',
            file='file1'
        )
        r_unequal2 = ihm.multi_state_scheme.RelaxationTime(
            value=1.0,
            unit='seconds',
            details='details1',
            dataset_group='dataset_group1',
            file='file1'
        )
        r_unequal3 = ihm.multi_state_scheme.RelaxationTime(
            value=1.0,
            unit='milliseconds',
            details='details2',
            dataset_group='dataset_group1',
            file='file1'
        )
        r_unequal4 = ihm.multi_state_scheme.RelaxationTime(
            value=1.0,
            unit='milliseconds',
            details='details',
            dataset_group='dataset_group2',
            file='file1'
        )
        r_unequal5 = ihm.multi_state_scheme.RelaxationTime(
            value=1.0,
            unit='milliseconds',
            details='details1',
            file='file1'
        )
        self.assertTrue(r_ref == r_equal)
        self.assertFalse(r_ref == r_unequal1)
        self.assertTrue(r_ref != r_unequal1)
        self.assertFalse(r_ref == r_unequal2)
        self.assertTrue(r_ref != r_unequal2)
        self.assertFalse(r_ref == r_unequal3)
        self.assertTrue(r_ref != r_unequal3)
        self.assertFalse(r_ref == r_unequal4)
        self.assertTrue(r_ref != r_unequal4)
        self.assertFalse(r_ref == r_unequal5)
        self.assertTrue(r_ref != r_unequal5)


if __name__ == '__main__':
    unittest.main()
