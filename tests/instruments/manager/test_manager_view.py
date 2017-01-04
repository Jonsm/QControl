# -*- coding: utf-8 -*-
# =============================================================================
# module : instruments/manager/test_manager_view.py
# author : Matthieu Dartiailh
# license : MIT license
# =============================================================================
"""
"""
import enaml

from .tools import BaseClass

with enaml.imports():
    from hqc_meas.instruments.manager.manifest import InstrManagerManifest
    from hqc_meas.instruments.manager.manager_view import InstrManagerView

from ...util import complete_line


def setup_module():
    print complete_line(__name__ + ': setup_module()', '~', 78)


def teardown_module():
    print complete_line(__name__ + ': teardown_module()', '~', 78)


class TestManagerView(BaseClass):

    mod = __name__
    dir_id = 2

    def test_form1(self):
        self.workbench.register(InstrManagerManifest())
        manager = self.workbench.get_plugin(u'hqc_meas.instr_manager')
        view = InstrManagerView(manager=manager)
        del view
