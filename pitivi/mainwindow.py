# -*- coding: utf-8 -*-
# Pitivi video editor
# Copyright (c) 2005, Edward Hervey <bilboed@bilboed.com>
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU Lesser General Public
# License as published by the Free Software Foundation; either
# version 2.1 of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public
# License along with this program; if not, write to the
# Free Software Foundation, Inc., 51 Franklin St, Fifth Floor,
# Boston, MA 02110-1301, USA.
"""Pitivi's main window."""
import os
from gettext import gettext as _
from urllib.parse import unquote

from gi.repository import Gio
from gi.repository import Gtk

from pitivi.configure import get_pixmap_dir
from pitivi.dialogs.about import AboutDialog
from pitivi.editorperspective import EditorPerspective
from pitivi.greeterperspective import GreeterPerspective
from pitivi.settings import GlobalSettings
from pitivi.utils.loggable import Loggable
from pitivi.utils.misc import show_user_manual


GlobalSettings.addConfigOption('mainWindowX',
                               section="main-window",
                               key="X", default=0, type_=int)
GlobalSettings.addConfigOption('mainWindowY',
                               section="main-window",
                               key="Y", default=0, type_=int)
GlobalSettings.addConfigOption('mainWindowWidth',
                               section="main-window",
                               key="width", default=-1, type_=int)
GlobalSettings.addConfigOption('mainWindowHeight',
                               section="main-window",
                               key="height", default=-1, type_=int)

GlobalSettings.addConfigSection('export')
GlobalSettings.addConfigOption('lastExportFolder',
                               section='export',
                               key="last-export-folder",
                               environment="PITIVI_EXPORT_FOLDER",
                               default=os.path.expanduser("~"))

GlobalSettings.addConfigSection("version")
GlobalSettings.addConfigOption('displayCounter',
                               section='version',
                               key='info-displayed-counter',
                               default=0)
GlobalSettings.addConfigOption('lastCurrentVersion',
                               section='version',
                               key='last-current-version',
                               default='')


class MainWindow(Gtk.ApplicationWindow, Loggable):
    """Pitivi's main window.

    It manages the UI and handles the switch between different perspectives,
    such as the default GreeterPerspective, and the EditorPerspective.

    Attributes:
        app (Pitivi): The app.
    """

    def __init__(self, app):
        gtksettings = Gtk.Settings.get_default()
        gtksettings.set_property("gtk-application-prefer-dark-theme", True)
        theme = gtksettings.get_property("gtk-theme-name")
        os.environ["GTK_THEME"] = theme + ":dark"

        # Pulseaudio "role"
        # (http://0pointer.de/blog/projects/tagging-audio.htm)
        os.environ["PULSE_PROP_media.role"] = "production"
        os.environ["PULSE_PROP_application.icon_name"] = "pitivi"

        Gtk.IconTheme.get_default().append_search_path(get_pixmap_dir())

        Gtk.ApplicationWindow.__init__(self)
        Loggable.__init__(self)

        self.log("Creating main window")

        self.app = app
        self.greeter = GreeterPerspective(app)
        self.editor = EditorPerspective(app)
        self.__perspective = None
        self.help_action = None
        self.about_action = None
        self.main_menu_action = None

        app.project_manager.connect("new-project-loading",
                                    self.__new_project_loading_cb)
        app.project_manager.connect("new-project-failed",
                                    self.__new_project_failed_cb)
        app.project_manager.connect("project-closed", self.__project_closed_cb)

    def setup_ui(self):
        """Sets up the various perspectives's UI."""
        self.log("Setting up the perspectives.")

        self.set_icon_name("pitivi")
        self.__check_screen_constraints()
        self.__set_keyboard_shortcuts()

        self.greeter.setup_ui()
        self.editor.setup_ui()

        width = self.app.settings.mainWindowWidth
        height = self.app.settings.mainWindowHeight

        if height == -1 and width == -1:
            self.maximize()
        else:
            self.set_default_size(width, height)
            self.move(self.app.settings.mainWindowX, self.app.settings.mainWindowY)

        self.connect("configure-event", self.__configure_cb)
        self.connect("delete-event", self.__delete_cb)

    def __check_screen_constraints(self):
        """Measures the approximate minimum size required by the main window.

        Shrinks some widgets to fit better on smaller screen resolutions.
        """
        # This code works, but keep in mind get_preferred_size's output
        # is only an approximation. As of 2015, GTK still does not have
        # a way, even with client-side decorations, to tell us the exact
        # minimum required dimensions of a window.
        min_size, _ = self.get_preferred_size()
        screen_width = self.get_screen().get_width()
        screen_height = self.get_screen().get_height()
        self.debug("Minimum UI size is %sx%s", min_size.width, min_size.height)
        self.debug("Screen size is %sx%s", screen_width, screen_height)
        if min_size.width >= 0.9 * screen_width:
            self.medialibrary.activateCompactMode()
            self.viewer.activateCompactMode()
            min_size, _ = self.get_preferred_size()
            self.info("Minimum UI size has been reduced to %sx%s",
                      min_size.width, min_size.height)

    def __set_keyboard_shortcuts(self):
        self.app.shortcuts.register_group("win", _("Project"), position=20)

        self.help_action = Gio.SimpleAction.new("help", None)
        self.help_action.connect("activate", self.__user_manual_cb)
        self.add_action(self.help_action)
        self.app.shortcuts.add("win.help", ["F1"], _("Help"), group="app")

        self.about_action = Gio.SimpleAction.new("about", None)
        self.about_action.connect("activate", self.__about_cb)
        self.add_action(self.about_action)
        self.app.shortcuts.add("win.about", ["<Primary><Shift>a"],
                               _("About"), group="app")

        self.main_menu_action = Gio.SimpleAction.new("menu-button", None)
        self.main_menu_action.connect("activate", self.__menu_cb)
        self.add_action(self.main_menu_action)
        self.app.shortcuts.add("win.menu-button", ["F10"],
                               _("Show the menu button content"), group="app")

    @staticmethod
    def __user_manual_cb(unused_action, unused_param):
        show_user_manual()

    def __about_cb(self, unused_action, unused_param):
        about_dialog = AboutDialog(self.app)
        about_dialog.show()

    def __menu_cb(self, unused_action, unused_param):
        self.__perspective.menu_button.set_active(
            not self.__perspective.menu_button.get_active())

    def __configure_cb(self, unused_widget, unused_event):
        """Saves the main window position and size."""
        # Takes window manager decorations into account.
        position = self.get_position()
        self.app.settings.mainWindowX = position.root_x
        self.app.settings.mainWindowY = position.root_y

        # Does not include the size of the window manager decorations.
        size = self.get_size()
        self.app.settings.mainWindowWidth = size.width
        self.app.settings.mainWindowHeight = size.height

    def __delete_cb(self, unused_widget, unused_data=None):
        self.app.settings.mainWindowHPanePosition = self.editor.secondhpaned.get_position()
        self.app.settings.mainWindowMainHPanePosition = self.editor.mainhpaned.get_position()
        self.app.settings.mainWindowVPanePosition = self.editor.toplevel_widget.get_position()

        if not self.app.shutdown():
            return True
        return False

    def __new_project_loading_cb(self, unused_project_manager, unused_project):
        self.show_perspective(self.editor)

    def __new_project_failed_cb(self, unused_project_manager, uri, reason):
        project_filename = unquote(uri.split("/")[-1])
        dialog = Gtk.MessageDialog(transient_for=self,
                                   modal=True,
                                   message_type=Gtk.MessageType.ERROR,
                                   buttons=Gtk.ButtonsType.OK,
                                   text=_('Unable to load project "%s"') % project_filename)
        dialog.set_property("secondary-use-markup", True)
        dialog.set_property("secondary-text", unquote(str(reason)))
        dialog.set_transient_for(self)
        dialog.run()
        dialog.destroy()
        self.show_perspective(self.greeter)

    def __project_closed_cb(self, unused_project_manager, unused_project):
        self.show_perspective(self.greeter)

    def show_perspective(self, perspective):
        """Displays the specified perspective."""
        if self.__perspective is perspective:
            return
        if self.__perspective:
            # Remove the current perspective before adding the
            # specified perspective because we can only add one
            # toplevel widget to the main window at a time.
            self.remove(self.__perspective.toplevel_widget)
        self.log("Displaying perspective: %s", type(perspective).__name__)
        self.__perspective = perspective
        self.set_titlebar(perspective.headerbar)
        self.add(perspective.toplevel_widget)
        perspective.refresh()
