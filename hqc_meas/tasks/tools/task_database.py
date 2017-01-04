# -*- coding: utf-8 -*-
# =============================================================================
# module : task_database.py
# author : Matthieu Dartiailh
# license : MIT license
# =============================================================================
"""
"""
from atom.api import Atom, Dict, Bool, Value, Event, List, Str, Typed
from threading import Lock


class DatabaseNode(Atom):
    """ Helper class to differentiate nodes and dict in database

    """
    data = Dict()

    meta = Dict()


class TaskDatabase(Atom):
    """ A database for inter tasks communication.

    The database has two modes:
        - an edition mode in which the number of entries and their hierarchy
        can change. In this mode the database is represented by a nested dict.
        - a running mode in which the entries are fixed (only their values can
        change). In this mode the database is represented as a flat list.
        In running mode the database is thread safe but the object it contains
        may not be so (dict, list, etc)

    """
    # --- Public API ----------------------------------------------------------

    #: Event used to notify a value changed in the database. Thye update is
    #: passed as a tuple (path, value)
    notifier = Event()

    #: List of root entries which should not be listed.
    excluded = List(Str(), ['threads', 'instrs'])

    #: Flag indicating whether or not the database entered the running mode. In
    #: running mode the database is flattened into a list for faster acces.
    running = Bool(False)

    def set_value(self, node_path, value_name, value):
        """Method used to set the value of the entry at the specified path

        This method can be used both in edition and running mode.

        Parameters:
        ----------
        node_path : str
            Path to the node holding the value to be set

        value_name : str
            Public key associated with the value to be set, internally
            converted so that we do not mix value and nodes

        value : any
            Actual value to be stored

        Returns
        -------
        new_val : bool
            Boolean indicating whether or not a new entry has been created in
            the database

        """
        new_val = False
        if self.running:
            full_path = node_path + '/' + value_name
            index = self._entry_index_map[full_path]
            self._lock.acquire()
            self._flat_database[index] = value
            self.notifier = (node_path + '/' + value_name, value)
            self._lock.release()
        else:
            node = self._go_to_path(node_path)
            if value_name not in node.data:
                new_val = True
            node.data[value_name] = value
            if new_val:
                self.notifier = (node_path + '/' + value_name, value)

        return new_val

    def get_value(self, assumed_path, value_name):
        """Method to get a value from the database from its name and a path

        This method returns the value stored under the specified name. It
        starts looking at the specified path and if necessary goes up in the
        hierarchy.

        Parameters
        ----------
        assumed_path : str
            Path where we start looking for the entry

        value_name : str
            Name of the value we are looking for

        Returns
        -------
        value : any
            Value stored under the entry value_name

        """
        if self.running:
            index = self._find_index(assumed_path, value_name)
            return self._flat_database[index]

        else:
            node = self._go_to_path(assumed_path)

            # First check if the entry is in the current node.
            if value_name in node.data:
                value = node.data[value_name]
                return value

            # Second check if there is a special rule about this entry.
            elif 'access' in node.meta and value_name in node.meta['access']:
                path = node.meta['access'][value_name]
                return self.get_value(path, value_name)

            # Finally go one step up in the node hierarchy.
            else:
                new_assumed_path = assumed_path.rpartition('/')[0]
                if assumed_path == new_assumed_path:
                    mes = "Can't find database entry : {}".format(value_name)
                    raise KeyError(mes)
                return self.get_value(new_assumed_path, value_name)

    def delete_value(self, node_path, value_name):
        """Method to remove an entry from the specified node

        This method remove the specified entry from the specified node. This
        method cannot be used in running mode.

        Parameters
        ----------
        assumed_path : str
            Path where we start looking for the entry

        value_name : str
            Name of the value we are looking for

        """
        if self.running:
            raise RuntimeError('Cannot delete an entry in running mode')

        else:
            node = self._go_to_path(node_path)

            if value_name in node.data:
                del node.data[value_name]
                self.notifier = (node_path + '/' + value_name,)
            else:
                err_str = 'No entry {} in node {}'.format(value_name,
                                                          node_path)
                raise ValueError(err_str)

    def get_values_by_index(self, indexes, prefix=None):
        """ Access to a list of values using the flat database.

        Parameters
        ----------
        indexes : list(int)
            List of index for which values should be returned.

        prefix : str, optional
            If provided return the values in dict with key of the form :
            prefix + index.

        Returns
        -------
        values : list or dict
            List of requested values in the same order as indexes or dict if
            prefix was not None.

        """
        if prefix is None:
            return [self._flat_database[i] for i in indexes]
        else:
            return {prefix + str(i): self._flat_database[i] for i in indexes}

    def get_entries_indexes(self, assumed_path, entries):
        """ Access to the index in the flattened database for some entries.

        Parameters
        ----------
        assumed_path : str
            Path to the node in which the values are assumed to be stored.

        entries : iterable(str)
            Names of the entries for which the indexes should be returned.

        Returns
        -------
        indexes : dict
            Dict mapping the entries names to their index in the flattened
            database.

        """
        return {name: self._find_index(assumed_path, name)
                for name in entries}

    def list_accessible_entries(self, node_path):
        """ Method used to get a list of all entries accessible from a node.

        DO NOT USE THIS METHOD IN RUNNING MODE (ie never in the check method
        of a task, use a try except clause instead and get_value or
        get_entries_indexes).

        Parameters:
        ----------
        node_path : str
            Path to the node from which accessible entries should be listed.

        Returns
        -------
        entries_list : list(str)
            List of entries accessible from the specified node

        """
        entries = []
        while node_path != 'root':
            node = self._go_to_path(node_path)
            keys = node.data.keys()
            # Looking for the entries in the node.
            for key in keys:
                if not isinstance(node.data[key], DatabaseNode):
                    entries.append(key)

            # Adding the special access if they are not already in the list.
            for entry in node.meta.get('access', []):
                if entry not in entries:
                    entries.append(entry)

            # Going to the next node.
            node_path = node_path.rpartition('/')[0]

        node = self._go_to_path(node_path)
        keys = node.data.keys()
        for key in keys:
            if not isinstance(node.data[key], DatabaseNode):
                entries.append(key)

        # Adding the special access if they are not already in the list.
        for entry in node.meta.get('access', []):
            if entry not in entries:
                entries.append(entry)

        for entry in self.excluded:
            if entry in entries:
                entries.remove(entry)

        return sorted(entries)

    def list_all_entries(self, path='root', values=False):
        """ List all entries in the database.

        Parameters
        ----------
        path : str, optional
            Starting node. This parameters is for internal use only.

        values : bool, optional
            Whether or not to retun the values associated with the entries.

        Returns
        -------
        paths : list(str) or dict is values
            List of all accessible entries with their full path.

        """
        entries = [] if not values else {}
        node = self._go_to_path(path)
        for entry in node.data.keys():
            if isinstance(node.data[entry], DatabaseNode):
                aux = self.list_all_entries(path=path + '/' + entry,
                                            values=values)
                if not values:
                    entries.extend(aux)
                else:
                    entries.update(aux)
            else:
                if not values:
                    entries.append(path + '/' + entry)
                else:
                    entries[path + '/' + entry] = node.data[entry]

        if path == 'root':
            for entry in self.excluded:
                aux = path + '/' + entry
                if aux in entries:
                    if not values:
                        entries.remove(aux)
                    else:
                        del entries[aux]

        return sorted(entries) if not values else entries

    def add_access_exception(self, node_path, entry, entry_node):
        """ Add an access exception in a node for an entry located in a node
        below.

        Parameters
        ----------
        node_path : str
            Path to the node which should hold the exception.

        entry : str
            Name of the entry for which to create an exception.

        entry_node : str
            Absolute path to the node holding the entry.

        """
        node = self._go_to_path(node_path)
        if 'access' in node.meta:
            access_exceptions = node.meta['access']
            access_exceptions[entry] = entry_node
        else:
            node.meta['access'] = {entry: entry_node}

    def remove_access_exception(self, node_path, entry=''):
        """ Remove an access exception from a node for a given entry.

        Parameters
        ----------
        node_path : str
            Path to the node holding the exception.

        entry : str, optional
            Name of the entry for which to remove the exception, if not
            provided all access exceptions will be removed.

        """
        node = self._go_to_path(node_path)
        if entry:
            access_exceptions = node.meta['access']
            del access_exceptions[entry]
        else:
            del node.meta['access']

    def create_node(self, parent_path, node_name):
        """Method used to create a new node in the database

        This method creates a new node in the database at the specified path.
        This method is not thread safe safe as the hierarchy of the tasks'
        database is not supposed to change during a measurement but only during
        the configuration phase

        Parameters:
        ----------
        parent_path : str
            Path to the node parent of the new one

        node_name : str
            Name of the new node to create

        """
        if self.running:
            raise RuntimeError('Cannot create a node in running mode')

        parent_node = self._go_to_path(parent_path)
        parent_node.data[node_name] = DatabaseNode()

    def rename_node(self, parent_path, new_name, old_name):
        """Method used to rename a node in the database

        This method renames the node at the specified path.
        This method is not thread safe safe as the hierarchy of the tasks'
        database is not supposed to change during a measurement but only during
        the configuration phase

        Parameters:
        ----------
        node_path : str
            Path to the node being renamed

        node_name : str
            New name of node

        """
        if self.running:
            raise RuntimeError('Cannot rename a node in running mode')

        parent_node = self._go_to_path(parent_path)
        parent_node.data[new_name] = parent_node.data[old_name]
        del parent_node.data[old_name]

    def delete_node(self, parent_path, node_name):
        """Method used to an existing node from the database

        This method deltes a node in the database at the specified path.
        This method is not thread safe safe as the hierarchy of the tasks'
        database is not supposed to change during a measurement but only during
        the configuration phase

        Parameters:
        ----------
        parent_path : str
            Path to the node parent of the new one

        node_name : str
            Name of the new node to create

        """
        if self.running:
            raise RuntimeError('Cannot delete a node in running mode')

        parent_node = self._go_to_path(parent_path)
        if node_name in parent_node.data:
            del parent_node.data[node_name]
        else:
            err_str = 'No node {} at the path {}'.format(node_name,
                                                         parent_path)
            raise ValueError(err_str)

    def prepare_for_running(self):
        """ Enter a thread safe, flat database state.

        This is used when tasks are executed.

        """
        self._lock = Lock()
        self.running = True

        # Flattening the database by walking all the nodes.
        index = 0
        nodes = [('root', self._database)]
        mapping = {}
        datas = []
        for (node_path, node) in nodes:
            for key, val in node.data.iteritems():
                path = node_path + '/' + key
                if isinstance(val, DatabaseNode):
                    nodes.append((path, val))
                else:
                    mapping[path] = index
                    index += 1
                    datas.append(val)

        # Walking a second time to add the exception to the _entry_index_map,
        # in reverse order in case an entry has multiple exceptions.
        for (node_path, node) in nodes[::-1]:
            access = node.meta.get('access', [])
            for entry in access:
                short_path = node_path + '/' + entry
                full_path = access[entry] + '/' + entry
                mapping[short_path] = mapping[full_path]

        self._flat_database = datas
        self._entry_index_map = mapping

        self._database = None

    # --- Private API ---------------------------------------------------------

    #: Main container for the database.
    _database = Typed(DatabaseNode, ())

    #: Flat version of the database only used in running mode for perfomances
    #: issues.
    _flat_database = List()

    #: Dict mapping full paths to flat database indexes.
    _entry_index_map = Dict()

    #: Lock to make the database thread safe in running mode.
    _lock = Value()

    def _go_to_path(self, path):
        """Method used to reach a node specified by a path.

        """
        node = self._database
        if path == 'root':
            return node

        # Decompose the path in database keys
        keys = path.split('/')
        # Remove first key (ie 'root' as we are not trying to access it)
        del keys[0]

        for key in keys:
            if key in node.data:
                node = node.data[key]
            else:
                ind = keys.index(key)
                if ind == 0:
                    err_str = \
                        'Path {} is invalid, no node {} in root'.format(path,
                                                                        key)
                else:
                    err_str = 'Path {} is invalid, no node {} in node\
                        {}'.format(path, key, keys[ind-1])
                raise ValueError(err_str)

        return node

    def _find_index(self, assumed_path, entry):
        """ Find the index associated with a path.

        Only to be used in running mode.

        """
        path = assumed_path
        while path != 'root':
            full_path = path + '/' + entry
            if full_path in self._entry_index_map:
                return self._entry_index_map[full_path]
            path = path.rpartition('/')[0]

        full_path = path + '/' + entry
        if full_path in self._entry_index_map:
            return self._entry_index_map[full_path]

        raise KeyError("Can't find entry matching {}, {}".format(assumed_path,
                       entry))
