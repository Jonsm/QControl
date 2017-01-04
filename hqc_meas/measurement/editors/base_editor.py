# -*- coding: utf-8 -*-
# =============================================================================
# module : base_editor.py
# author : Matthieu Dartiailh
# license : MIT license
# =============================================================================
from atom.api import (Callable, Unicode, Instance, Bool, ForwardTyped, Event)
from enaml.core.declarative import Declarative, d_
from enaml.widgets.api import Page

from hqc_meas.tasks.api import BaseTask


class BaseEditor(Page):
    """ Base class for all editors.

    """
    #: Declaration defining this editor.
    declaration = ForwardTyped(lambda: Editor)

    #: Currently selected task in the tree.
    selected_task = d_(Instance(BaseTask))

    #: The framework fires this event any time the editor becomes selected.
    selected = d_(Event())

    #: The framework fires this event any time the editor is unselected.
    unselected = d_(Event())

    #: Should the tree be visible when this editor is selected.
    tree_visible = d_(Bool(True))

    #: Should the tree be enabled when this editor is selected.
    tree_enabled = d_(Bool(True))


class Editor(Declarative):
    """ Extension for the 'editors' extension point of a MeasurePlugin.

    The name member inherited from Object should always be set to an easily
    understandable name for the user.

    """
    # Id of the editor, this can be different from the id of the plugin
    # declaring it but does not have to.
    id = d_(Unicode())

    # Editor description.
    description = d_(Unicode())

    # Factory function returning an instance of the editor. This callable
    # should take as arguments the editor declaration and the workbench.
    factory = d_(Callable())

    # Test function determining if the editor is fit to be used for the
    # selected task. This function should take as arguments the workbench and
    # the selected task and return a boolean.
    test = d_(Callable(lambda workbench, selected_task: True))
