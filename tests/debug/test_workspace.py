# -*- coding: utf-8 -*-
#==============================================================================
# module : test_workspace.py
# author : Matthieu Dartiailh
# license : MIT license
#==============================================================================
import enaml
from enaml.workbench.api import Workbench
import os
import logging
from configobj import ConfigObj
from nose.tools import (assert_in, assert_not_in, assert_equal, assert_true,
                        assert_is_instance, assert_false)

from hqc_meas.debug.debugger_workspace import LOG_ID
with enaml.imports():
    from enaml.workbench.core.core_manifest import CoreManifest
    from enaml.workbench.ui.ui_manifest import UIManifest
    from hqc_meas.utils.state.manifest import StateManifest
    from hqc_meas.utils.preferences.manifest import PreferencesManifest
    from hqc_meas.utils.log.manifest import LogManifest
    from hqc_meas.tasks.manager.manifest import TaskManagerManifest
    from hqc_meas.instruments.manager.manifest import InstrManagerManifest
    from hqc_meas.debug.debugger_manifest import DebuggerManifest
    from hqc_meas.app_manifest import HqcAppManifest

    from .helpers import (TestSuiteManifest, TestDebugger, TestDebuggerView,
                          tester)

from ..util import (complete_line, process_app_events, close_all_windows,
                    remove_tree, create_test_dir)


def setup_module():
    print complete_line(__name__ + ': setup_module()', '~', 78)


def teardown_module():
    print complete_line(__name__ + ': teardown_module()', '~', 78)


class TestDebugSpace(object):

    test_dir = ''

    @classmethod
    def setup_class(cls):
        print complete_line(__name__ +
                            ':{}.setup_class()'.format(cls.__name__), '-', 77)
        # Creating dummy directory for prefs (avoid prefs interferences).
        directory = os.path.dirname(__file__)
        cls.test_dir = os.path.join(directory, '_temps')
        create_test_dir(cls.test_dir)

        # Creating dummy default.ini file in utils.
        util_path = os.path.join(directory, '..', '..', 'hqc_meas', 'utils',
                                 'preferences')
        def_path = os.path.join(util_path, 'default.ini')

        # Making the preference manager look for info in test dir.
        default = ConfigObj(def_path)
        default['folder'] = cls.test_dir
        default['file'] = 'default_test.ini'
        default.write()

        conf = ConfigObj(os.path.join(cls.test_dir, 'default_test.ini'))
        conf.write()

    @classmethod
    def teardown_class(cls):
        print complete_line(__name__ +
                            ':{}.teardown_class()'.format(cls.__name__), '-',
                            77)
        # Removing pref files creating during tests.
        remove_tree(cls.test_dir)

        # Restoring default.ini file in utils
        directory = os.path.dirname(__file__)
        util_path = os.path.join(directory, '..', '..', 'hqc_meas', 'utils',
                                 'preferences')
        def_path = os.path.join(util_path, 'default.ini')
        os.remove(def_path)

    def setup(self):

        self.workbench = Workbench()
        self.workbench.register(CoreManifest())
        self.workbench.register(UIManifest())
        self.workbench.register(HqcAppManifest())
        self.workbench.register(StateManifest())
        self.workbench.register(PreferencesManifest())
        self.workbench.register(LogManifest())
        self.workbench.register(TaskManagerManifest())
        self.workbench.register(InstrManagerManifest())
        self.workbench.register(DebuggerManifest())
        self.workbench.register(TestSuiteManifest())

    def teardown(self):
        core = self.workbench.get_plugin(u'enaml.workbench.core')
        core.invoke_command(u'enaml.workbench.ui.close_workspace', {}, self)
        self.workbench.unregister(u'hqc_meas.debug')
        self.workbench.unregister(u'tests.suite')
        self.workbench.unregister(u'hqc_meas.task_manager')
        self.workbench.unregister(u'hqc_meas.instr_manager')
        self.workbench.unregister(u'hqc_meas.logging')
        self.workbench.unregister(u'hqc_meas.preferences')
        self.workbench.unregister(u'hqc_meas.state')
        self.workbench.unregister(u'hqc_meas.app')
        self.workbench.unregister(u'enaml.workbench.ui')
        self.workbench.unregister(u'enaml.workbench.core')
        close_all_windows()

    def test_life_cycle1(self):
        """ Test that workspace starting/closing goes well.

        """
        plugin = self.workbench.get_plugin(u'hqc_meas.debug')

        core = self.workbench.get_plugin(u'enaml.workbench.core')
        cmd = u'enaml.workbench.ui.select_workspace'
        core.invoke_command(cmd, {'workspace': u'hqc_meas.debug.workspace'},
                            self)

        log_plugin = self.workbench.get_plugin(u'hqc_meas.logging')

        # Check the plugin got the workspace
        assert_true(plugin.workspace)
        workspace = plugin.workspace

        # Check the contribution of the debugger was added to the workspace.
        assert_true(tester.contributing)

        ui = self.workbench.get_plugin('enaml.workbench.ui')
        ui.show_window()
        process_app_events()

        # Check the workspace registration.
        assert_true(workspace.log_model)
        assert_in(LOG_ID, log_plugin.handler_ids)

        logger = logging.getLogger(__name__)
        logger.info('test')
        process_app_events()
        assert_in('test', workspace.log_model.text)

        cmd = u'enaml.workbench.ui.close_workspace'
        core.invoke_command(cmd, {}, self)

        # Check the workspace removed its log handler.
        assert_not_in(LOG_ID, log_plugin.handler_ids)

        # Check the reference to the workspace was destroyed.
        assert_equal(plugin.workspace, None)

        # Check the contribution of the debugger to the workspace was removed.
        assert_false(tester.contributing)

    def test_life_cycle2(self):
        """ Test that workspace reselection do restore debug panels.

        """
        plugin = self.workbench.get_plugin(u'hqc_meas.debug')

        core = self.workbench.get_plugin(u'enaml.workbench.core')
        cmd = u'enaml.workbench.ui.select_workspace'
        core.invoke_command(cmd, {'workspace': u'hqc_meas.debug.workspace'},
                            self)

        # Check the plugin got the workspace
        assert_true(plugin.workspace)
        workspace = plugin.workspace
        ui = self.workbench.get_plugin('enaml.workbench.ui')
        ui.show_window()
        process_app_events()

        # Creating debuggers.
        workspace.create_debugger('debugger1')
        process_app_events()

        workspace.create_debugger('debugger1')
        process_app_events()

        d_view1 = workspace.dock_area.find('item_1')
        assert_is_instance(d_view1, TestDebuggerView)
        d_view2 = workspace.dock_area.find('item_2')
        assert_is_instance(d_view2, TestDebuggerView)

        del workspace
        # Closing workspace
        cmd = u'enaml.workbench.ui.close_workspace'
        core.invoke_command(cmd, {}, self)
        process_app_events()

        # Check the debugger released their ressources.
        for debugger in plugin.debugger_instances:
            assert_true(debugger.released)

        # Reopening workspace.
        cmd = u'enaml.workbench.ui.select_workspace'
        core.invoke_command(cmd, {'workspace': u'hqc_meas.debug.workspace'},
                            self)
        process_app_events()

        workspace = plugin.workspace

        # Checking the debuggers are there.
        dock_area = workspace.dock_area
        d_view1 = dock_area.find('item_1')
        assert_is_instance(d_view1, TestDebuggerView)
        d_view2 = dock_area.find('item_2')
        assert_is_instance(d_view2, TestDebuggerView)

    def test_create_debugger1(self):
        """ Creating a debugger.

        """
        plugin = self.workbench.get_plugin(u'hqc_meas.debug')

        core = self.workbench.get_plugin(u'enaml.workbench.core')
        cmd = u'enaml.workbench.ui.select_workspace'
        core.invoke_command(cmd, {'workspace': u'hqc_meas.debug.workspace'},
                            self)

        # Check the plugin got the workspace
        assert_true(plugin.workspace)
        workspace = plugin.workspace
        ui = self.workbench.get_plugin('enaml.workbench.ui')
        ui.show_window()
        process_app_events()

        workspace.create_debugger('debugger1')
        process_app_events()

        assert_true(plugin.debugger_instances)
        assert_is_instance(plugin.debugger_instances[0], TestDebugger)

        dock_area = workspace.dock_area
        d_view = dock_area.find('item_1')
        assert_is_instance(d_view, TestDebuggerView)

    def test_create_debugger2(self):
        """ Creating a debugger with wrong id.

        """
        plugin = self.workbench.get_plugin(u'hqc_meas.debug')

        core = self.workbench.get_plugin(u'enaml.workbench.core')
        cmd = u'enaml.workbench.ui.select_workspace'
        core.invoke_command(cmd, {'workspace': u'hqc_meas.debug.workspace'},
                            self)

        # Check the plugin got the workspace
        assert_true(plugin.workspace)
        workspace = plugin.workspace
        ui = self.workbench.get_plugin('enaml.workbench.ui')
        ui.show_window()
        process_app_events()

        workspace.create_debugger('debugger_false')
        process_app_events()

        assert_false(plugin.debugger_instances)

    def test_closing_debugger_panel(self):
        """ Test closing a debugger panel and reopening one.

        """
        plugin = self.workbench.get_plugin(u'hqc_meas.debug')

        core = self.workbench.get_plugin(u'enaml.workbench.core')
        cmd = u'enaml.workbench.ui.select_workspace'
        core.invoke_command(cmd, {'workspace': u'hqc_meas.debug.workspace'},
                            self)

        # Check the plugin got the workspace
        assert_true(plugin.workspace)
        workspace = plugin.workspace
        ui = self.workbench.get_plugin('enaml.workbench.ui')
        ui.show_window()
        process_app_events()

        workspace.create_debugger('debugger1')
        process_app_events()
        workspace.create_debugger('debugger1')
        process_app_events()
        workspace.create_debugger('debugger1')
        process_app_events()

        debugger = plugin.debugger_instances[1]

        item = workspace.dock_area.find('item_2')
        item.proxy.widget.close()
        process_app_events()
        item.destroy()
        process_app_events()

        assert_equal(len(workspace.dock_area.dock_items()), 3)
        assert_equal(len(plugin.debugger_instances), 2)
        assert_true(debugger.released)

        workspace.create_debugger('debugger1')
        process_app_events()

        assert_equal(len(plugin.debugger_instances), 3)
        assert_true(workspace.dock_area.find('item_2'))
