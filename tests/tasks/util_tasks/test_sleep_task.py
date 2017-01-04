# -*- coding: utf-8 -*-
# ============================================================
# module : test_sleep_task.py
# author : Matthieu Dartiailh
# license : MIT license
# ============================================================
"""
"""
from nose.tools import (assert_equal, assert_true, assert_false, assert_in)
from nose.plugins.attrib import attr
from multiprocessing import Event
from enaml.workbench.api import Workbench

from hqc_meas.tasks.api import RootTask
from hqc_meas.tasks.tasks_util.sleep_task import SleepTask

import enaml
with enaml.imports():
    from enaml.workbench.core.core_manifest import CoreManifest
    from hqc_meas.utils.state.manifest import StateManifest
    from hqc_meas.utils.preferences.manifest import PreferencesManifest
    from hqc_meas.tasks.manager.manifest import TaskManagerManifest

    from hqc_meas.tasks.tasks_util.views.sleep_task_view import SleepView

from ...util import process_app_events, close_all_windows


class TestSleepTask(object):

    def setup(self):
        self.root = RootTask(should_stop=Event(), should_pause=Event())
        self.task = SleepTask(task_name='Test')
        self.root.children_task.append(self.task)

    def test_check1(self):
        # Simply test that everything is ok if time > 0.
        self.task.time = 1.0

        test, traceback = self.task.check()
        assert_true(test)
        assert_false(traceback)

    def test_check2(self):
        # Test handling a wrong message.
        self.task.time = -1.0

        test, traceback = self.task.check()
        assert_false(test)
        assert_equal(len(traceback), 1)
        assert_in('root/Test', traceback)

    def test_perform(self):
        # Test performing when condition is True.
        self.root.task_database.prepare_for_running()

        self.task.perform()


@attr('ui')
class TestSleepView(object):

    def setup(self):
        self.workbench = Workbench()
        self.workbench.register(CoreManifest())
        self.workbench.register(StateManifest())
        self.workbench.register(PreferencesManifest())
        self.workbench.register(TaskManagerManifest())

        self.root = RootTask(should_stop=Event(), should_pause=Event())
        self.task = SleepTask(task_name='Test', time=0.0)
        self.root.children_task.append(self.task)

    def teardown(self):
        close_all_windows()

        self.workbench.unregister(u'hqc_meas.task_manager')
        self.workbench.unregister(u'hqc_meas.preferences')
        self.workbench.unregister(u'hqc_meas.state')
        self.workbench.unregister(u'enaml.workbench.core')

    def test_view(self):
        # Intantiate a view with no selected interface and select one after
        window = enaml.widgets.api.Window()
        view = SleepView(window, task=self.task)
        window.show()

        process_app_events()

        assert_equal(view.widgets()[1].text, '0.0')

        view.widgets()[1].text = '1.0'
        process_app_events()
        assert_equal(self.task.time, 1.0)
