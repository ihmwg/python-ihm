# coding=utf-8

"""Classes for handling connected/ordered schemes formed by multiple state
    together with information on kinetic schemes"""
import ihm.multi_state_scheme


class MultiStateScheme(object):
    """MultiStateScheme collects information about a collection of
       multiple states, that can form a connected/ordered scheme.
       A special case is a kinetic scheme, for which kinetic rates and
       relaxation times are available.

       :param str name: The name of the multi-state scheme.
       :param str details: Details on the scheme.
       :param list_of_connectivities: A list of connectivities that belong to
        the scheme.
       :type list_of_connectivities: List of
        :class:`ìhm.MultiStateSchemeConnectivity`
       :param list_of_relaxation_times: A list of relaxation times not assigned
        to specific connectivities, but to the scheme
       :type list_of_relaxation_times: List of :class:`ihm.RelaxationTime`
    """
    def __init__(self, name, details=None, list_of_connectivities=None,
                 list_of_relaxation_times=None):
        self.name = name
        self.details = details
        self.connectivity_list = []
        self.relaxation_time_list = []
        self.states = []  # filled automatically based on the connectivity_list

        if list_of_connectivities is not None:
            for c in list_of_connectivities:
                if c not in self.connectivity_list:
                    self.add_connectivity(c)
        if list_of_relaxation_times is not None:
            for r in list_of_relaxation_times:
                if r not in self.relaxation_time_list:
                    self.add_relaxation_time(r)

    def add_connectivity(self, connectivity):
        """Add a connectivity to the scheme.

        :param connectivity: The connectivity to add to the scheme
        :type connectivity: :class:`MultiStateSchemeConnectivity`
        """
        if connectivity not in self.connectivity_list:
            # Make sure that the connectivity has not been assigned to
            # another scheme
            if not connectivity._assigned_to_scheme:
                connectivity.set_assigned_to_scheme()
                self.connectivity_list.append(connectivity)
            # If the connectivity has beedn assigned to another scheme,
            # create a copy of the connectivity and use that
            else:
                old_connectivity = connectivity
                connectivity = \
                    ihm.multi_state_scheme.MultiStateSchemeConnectivity(
                        begin_state=old_connectivity.begin_state,
                        end_state=old_connectivity.end_state,
                        details=old_connectivity.details,
                        dataset_group=old_connectivity.dataset_group,
                        kinetic_rate=old_connectivity.kinetic_rate,
                        relaxation_time=old_connectivity.relaxation_time
                    )
                connectivity.set_assigned_to_scheme()
                self.connectivity_list.append(connectivity)

        # Add the states that belong to the connectivity
        if connectivity.begin_state not in self.states:
            self.states.append(connectivity.begin_state)
        if (connectivity.end_state is not None) and \
                (connectivity.end_state not in self.states):
            self.states.append(connectivity.end_state)

    def add_relaxation_time(self, relaxation_time):
        """Add a relaxation time to the scheme. This relaxation time is not
        assigned to a connectivity.

        :param relaxation_time: The relaxation time to add to the scheme.
        :type relaxation_time: :class:`RelaxationTime`
        """
        self.relaxation_time_list.append(relaxation_time)

    def __eq__(self, other):
        return ((self.__dict__ == other.__dict__)
                and (self.connectivity_list == other.connectivity_list)
                and (self.relaxation_time_list == other.relaxation_time_list))


class MultiStateSchemeConnectivity(object):
    """A connectivity between states. Used to describe the directed
    edge of graph.
    If no end_state is given, the state is not connected to another state.
    This could be the case for states where no connection to other states
    could be resolved.

    :param begin_state: The start state of the connectivity.
    :type begin_state: :class:`ihm.model.State`
    :param end_state: The end state of the connectivity. Can be None in case
     of states that are not connected to others.
    :type end_state: :class:`ìhm.model.State`
    :param details: Details to the connectivity.
    :param dataset_group: The DatasetGroup that was used to obtain information
    on the connectivity.
    :type dataset_group: :class:`ìhm.dataset.DatasetGroup`
    :param kinetic_rate: A kinetic rate assigned to the connectivity.
    :type kinetic_rate: :class:`KineticRate`
    :param relaxation_time: A relaxation time assigned to the connectivity.
    :type relaxation_time: :class:`RelaxationTime`
    """
    def __init__(self, begin_state, end_state=None, details=None,
                 dataset_group=None, kinetic_rate=None, relaxation_time=None):
        self.begin_state = begin_state
        self.end_state = end_state
        self.details = details
        self.dataset_group = dataset_group
        self.kinetic_rate = kinetic_rate
        self.relaxation_time = relaxation_time
        # The _assigned_to_scheme variable tracks whether the connectivity
        # has been assigned to a scheme. This is to ensure that each
        # connectivity is only assigned to a single scheme.
        self._assigned_to_scheme = False

    def set_assigned_to_scheme(self):
        self._assigned_to_scheme = True

    def __eq__(self, other):
        return self.__dict__ == other.__dict__


class KineticRate(object):
    """A kinetic rate that can be assigned to a connectivity.
    The kinetic rate could be either a transition_rate_constant or
    an equilibrium_constant.
    In case of an equilibrium_constant, the equilibrium_constant_unit and
    equilibrium_constant_determination_method are required.

    :param float transition_rate_constant: A transition rate constant
      describing the exchange between two states. Unit: per second.
    :param float equilibrium_constant: An equilibrium constant describing the
      exchange between two states
    :param str equilibrium_constant_determination_method:
      The method how the equilibrium_constant was determined.
      Options are: ['equilibrium constant is determined from population',
      'equilibrium constant is determined from kinetic rates, kAB/kBA',
      'equilibrium constant is determined from another method not listed']
    :param str equilibrium_constant_unit: Unit of the equilibrium constant.
      Depending on what the process described,a unit might be applicable or not
    :param str details: Details on the kinetic rate.
    :param dataset_group: The DatasetGroup used to determine the kinetic rate.
    :type dataset_group: :class:`ihm.dataset.DatasetGroup`
    :param external_file: External file containing measurement data
      for the kinetic rate.

    """

    def __init__(self, transition_rate_constant=None,
                 equilibrium_constant=None,
                 equilibrium_constant_determination_method=None,
                 equilibrium_constant_unit=None,
                 details=None,
                 dataset_group=None,
                 external_file=None):
        self.allowed_eq_const_det_methods = [
            'equilibrium constant is determined from population',
            'equilibrium constant is determined from kinetic rates, kAB/kBA',
            'equilibrium constant is determined from another method not listed'
        ]
        self.transition_rate_constant = transition_rate_constant
        self.equilibrium_constant = equilibrium_constant
        self.equilibrium_constant_unit = equilibrium_constant_unit
        # check whether the equilibrium_constant_determination_method is
        # within the list of options if an equilibrium constant is given
        if self.equilibrium_constant is not None:
            if equilibrium_constant_determination_method not in \
                    self.allowed_eq_const_det_methods:
                raise ValueError(
                    "Error in KineticRate: Equilibrium determination method "
                    "\"%s\" is not in the list of allowed values. "
                    "Options are: %s" % (
                        equilibrium_constant_determination_method, ";".join(
                            ["\'%s\'" % (x) for x in
                             self.allowed_eq_const_det_methods])))
        self.equilibrium_constant_determination_method = \
            equilibrium_constant_determination_method
        self.details = details
        self.dataset_group = dataset_group
        self.external_file = external_file

    def __eq__(self, other):
        return self.__dict__ == other.__dict__


class RelaxationTime(object):
    """A relaxation time determined for a scheme.
    The relaxation time can either be connected to a specific connectivity
    in the scheme or to the scheme in general if no assignment is possible.

    :param float value: The relaxation time.
    :param str unit: The unit of the relaxation time. Options are
     ['seconds','milliseconds', microseconds']
    :param float amplitude: The amplitude of the relaxation time if determined.
    :param str details: Details on the relaxation time.
    :param dataset_group: DatasetGroup used to determine the relaxation time.
    :type dataset_group: :class:`ihm.dataset.DatasetGroup`
    :param external_file: An external file containing measurement data for
     the relaxation time.

    """
    def __init__(self, value, unit, amplitude=None,
                 details=None, dataset_group=None, external_file=None):
        self.list_of_allowed_relaxation_time_units = ['seconds',
                                                      'milliseconds',
                                                      'microseconds']

        self.value = value
        self.unit = unit
        self.amplitude = amplitude
        self.details = details
        self.dataset_group = dataset_group
        self.external_file = external_file

    def __eq__(self, other):
        return self.__dict__ == other.__dict__
