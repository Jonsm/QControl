# -*- coding: utf-8 -*-
# =============================================================================
# module : test_database.py
# author : Matthieu Dartiailh
# license : MIT license
# =============================================================================
from nose.tools import (raises, assert_equal, assert_false, assert_true,
                        assert_raises)
from hqc_meas.tasks.tools.task_database import TaskDatabase

from ..util import complete_line


def setup_module():
    print complete_line(__name__ + ': setup_module()', '~', 78)


def teardown_module():
    print complete_line(__name__ + ': teardown_module()', '~', 78)


# --- Edition mode tests.

def test_database_nodes():
    # Test all nodes operations.
    database = TaskDatabase()
    database.create_node('root', 'node1')
    database.create_node('root/node1', 'node2')
    database.rename_node('root', 'n_node1', 'node1')
    database.delete_node('root/n_node1', 'node2')


def test_database_values():
    # Test get/set value operations.
    database = TaskDatabase()
    assert_true(database.set_value('root', 'val1', 1))
    assert_equal(database.get_value('root', 'val1'), 1)
    assert_false(database.set_value('root', 'val1', 2))
    database.create_node('root', 'node1')
    database.set_value('root/node1', 'val2', 'a')
    assert_equal(database.get_value('root/node1', 'val2'), 'a')
    assert_equal(database.get_value('root/node1', 'val1'), 2)


@raises(KeyError)
def test_database_values2():
    # Test delete value operation.
    database = TaskDatabase()
    database.set_value('root', 'val1', 1)
    assert_equal(database.get_value('root', 'val1'), 1)
    database.delete_value('root', 'val1')
    database.get_value('root', 'val1')


@raises(KeyError)
def test_database_values3():
    # Test delete value operation.
    database = TaskDatabase()
    database.create_node('root', 'node1')
    database.create_node('root/node1', 'node2')
    database.set_value('root/node1/node2', 'val1', 1)
    assert_equal(database.get_value('root/node1/node2', 'val1'), 1)
    database.get_value('root/node1', 'val1')


def test_database_listing():
    # Test database entries listing.
    database = TaskDatabase()
    database.set_value('root', 'val1', 1)
    database.create_node('root', 'node1')
    database.set_value('root/node1', 'val2', 'a')

    assert_equal(database.list_all_entries(),
                 sorted(['root/val1', 'root/node1/val2']))
    assert_equal(database.list_all_entries(values=True),
                 {'root/val1': 1, 'root/node1/val2': 'a'})
    assert_equal(database.list_accessible_entries('root'), ['val1'])
    assert_equal(database.list_accessible_entries('root/node1'),
                 sorted(['val1', 'val2']))

    database.excluded = ['val1']
    assert_equal(database.list_all_entries(),
                 sorted(['root/node1/val2']))
    assert_equal(database.list_accessible_entries('root'), [])
    assert_equal(database.list_accessible_entries('root/node1'),
                 sorted(['val2']))


def test_access_exceptions1():
    # Test simple access exceptions.
    database = TaskDatabase()
    database.set_value('root', 'val1', 1)
    database.create_node('root', 'node1')
    database.set_value('root/node1', 'val2', 'a')
    database.create_node('root', 'node2')
    database.set_value('root/node2', 'val3', 2.0)

    assert_equal(database.list_accessible_entries('root'), ['val1'])

    database.add_access_exception('root', 'val2', 'root/node1')
    assert_equal(database.list_accessible_entries('root'), ['val1', 'val2'])
    assert_equal(database.get_value('root', 'val2'), 'a')

    database.add_access_exception('root', 'val3', 'root/node2')
    assert_equal(database.list_accessible_entries('root'),
                 ['val1', 'val2', 'val3'])
    assert_equal(database.get_value('root', 'val3'), 2.0)

    database.remove_access_exception('root', 'val2')
    assert_equal(database.list_accessible_entries('root'), ['val1', 'val3'])

    database.remove_access_exception('root')
    assert_equal(database.list_accessible_entries('root'), ['val1'])


def test_access_exceptions2():
    # Test nested access exceptions.
    database = TaskDatabase()
    database.set_value('root', 'val1', 1)
    database.create_node('root', 'node1')
    database.set_value('root/node1', 'val2', 'a')
    database.create_node('root/node1', 'node2')
    database.set_value('root/node1/node2', 'val3', 2.0)

    assert_equal(database.list_accessible_entries('root'), ['val1'])

    assert_raises(KeyError, database.get_value, 'root', 'val2')
    assert_raises(KeyError, database.get_value, 'root/node1', 'val3')

    database.add_access_exception('root/node1', 'val3', 'root/node1/node2')

    assert_raises(KeyError, database.get_value, 'root', 'val3')

    database.add_access_exception('root', 'val3', 'root/node1')
    assert_equal(database.list_accessible_entries('root'), ['val1', 'val3'])
    assert_equal(database.get_value('root', 'val3'), 2.0)

    database.remove_access_exception('root', 'val3')

    assert_raises(KeyError, database.get_value, 'root', 'val3')

    assert_equal(database.list_accessible_entries('root'), ['val1'])
    assert_equal(database.list_accessible_entries('root/node1'),
                 ['val1', 'val2', 'val3'])

    database.remove_access_exception('root/node1', 'val3')

    assert_raises(KeyError, database.get_value, 'root/node1', 'val3')
    assert_equal(database.list_accessible_entries('root/node1'),
                 ['val1', 'val2'])


# --- Running mode tests.

def test_flattening_database1():
    database = TaskDatabase()
    database.set_value('root', 'val1', 1)
    database.create_node('root', 'node1')
    database.set_value('root/node1', 'val2', 'a')

    database.prepare_for_running()


def test_index_op_on_flat_database1():
    # Test operation on flat database relying on indexes.
    database = TaskDatabase()
    database.set_value('root', 'val1', 1)
    database.create_node('root', 'node1')
    database.set_value('root/node1', 'val2', 'a')
    database.create_node('root/node1', 'node2')

    database.prepare_for_running()
    assert_equal(database.get_entries_indexes('root', ['val1']), {'val1': 0})
    assert_equal(database.get_entries_indexes('root/node1', ['val1', 'val2']),
                 {'val1': 0, 'val2': 1})
    assert_equal(database.get_entries_indexes('root/node1/node2', ['val2']),
                 {'val2': 1})

    assert_equal(database.get_values_by_index([0, 1]), [1, 'a'])
    assert_equal(database.get_values_by_index([0, 1], 'e_'),
                 {'e_0': 1, 'e_1': 'a'})


def test_index_op_on_flat_database2():
    # Test operation on flat database relying on indexes when a simple access
    # ex exists.
    database = TaskDatabase()
    database.set_value('root', 'val1', 1)
    database.create_node('root', 'node1')
    database.set_value('root/node1', 'val2', 'a')
    database.add_access_exception('root', 'val2', 'root/node1')

    database.prepare_for_running()
    assert_equal(database.get_entries_indexes('root', ['val1']), {'val1': 0})
    assert_equal(database.get_entries_indexes('root', ['val1', 'val2']),
                 {'val1': 0, 'val2': 1})


def test_index_op_on_flat_database3():
    # Test operation on flat database relying on indexes when a nested access
    # ex exists.
    database = TaskDatabase()
    database.set_value('root', 'val1', 1)
    database.create_node('root', 'node1')
    database.create_node('root/node1', 'node2')
    database.set_value('root/node1/node2', 'val2', 'a')
    database.add_access_exception('root/node1', 'val2', 'root/node1/node2')
    database.add_access_exception('root', 'val2', 'root/node1')

    database.prepare_for_running()
    assert_equal(database.get_entries_indexes('root', ['val1']), {'val1': 0})
    assert_equal(database.get_entries_indexes('root', ['val1', 'val2']),
                 {'val1': 0, 'val2': 1})


def test_get_set_on_flat_database1():
    # Test get/set operations on flat database using names.
    database = TaskDatabase()
    database.set_value('root', 'val1', 1)
    database.create_node('root', 'node1')
    database.set_value('root/node1', 'val2', 'a')

    database.prepare_for_running()
    assert_false(database.set_value('root', 'val1', 2))
    assert_equal(database.get_value('root', 'val1'), 2)
    assert_equal(database.get_value('root/node1', 'val1'), 2)


def test_get_set_on_flat_database2():
    # Test get/set operations on flat database using names when an access ex
    # exists.
    database = TaskDatabase()
    database.set_value('root', 'val1', 1)
    database.create_node('root', 'node1')
    database.set_value('root/node1', 'val2', 'a')
    database.add_access_exception('root', 'val2', 'root/node1')

    database.prepare_for_running()
    assert_false(database.set_value('root', 'val2', 2))
    assert_equal(database.get_value('root', 'val2'), 2)


def test_get_set_on_flat_database3():
    # Test get/set operations on flat database using names when a nested
    # access ex exists.
    database = TaskDatabase()
    database.set_value('root', 'val1', 1)
    database.create_node('root', 'node1')
    database.create_node('root/node1', 'node2')
    database.set_value('root/node1/node2', 'val2', 'a')
    database.add_access_exception('root/node1', 'val2', 'root/node1/node2')
    database.add_access_exception('root', 'val2', 'root/node1')

    database.prepare_for_running()
    assert_false(database.set_value('root', 'val2', 2))
    assert_equal(database.get_value('root', 'val2'), 2)

    assert_false(database.set_value('root/node1', 'val2', 2))
    assert_equal(database.get_value('root/node1', 'val2'), 2)
