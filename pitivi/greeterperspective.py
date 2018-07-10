# -*- coding: utf-8 -*-
# Pitivi video editor
# Copyright (c) 2010 Mathieu Duponchelle <seeed@laposte.net>
# Copyright (c) 2018 Harish Fulara <harishfulara1996@gmail.com>
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
"""Pitivi's Welcome/Greeter perspective."""
import os
from gettext import gettext as _

from gi.repository import Gdk
from gi.repository import GES
from gi.repository import Gio
from gi.repository import Gtk

from pitivi.configure import get_ui_dir
from pitivi.dialogs.browseprojects import BrowseProjectsDialog
from pitivi.perspective import Perspective
from pitivi.utils.ui import beautify_last_updated_timestamp
from pitivi.utils.ui import beautify_project_path
from pitivi.utils.ui import fix_infobar
from pitivi.utils.ui import GREETER_PERSPECTIVE_CSS

MAX_RECENT_PROJECTS = 10


class ProjectInfoRow(Gtk.ListBoxRow):
    """Displays a project's info.

    Attributes:
        recent_project_item (Gtk.RecentInfo): Recent project's meta-data.
    """
    def __init__(self, recent_project_item):
        Gtk.ListBoxRow.__init__(self)
        self.uri = recent_project_item.get_uri()
        self.name = os.path.splitext(recent_project_item.get_display_name())[0]

        builder = Gtk.Builder()
        builder.add_from_file(os.path.join(get_ui_dir(), "project_info.ui"))
        self.add(builder.get_object("project_info_tophbox"))

        self.select_button = builder.get_object("project_select_button")
        # Hide the select button as we only want to
        # show it during projects removal screen.
        self.select_button.hide()

        builder.get_object("project_name_label").set_text(self.name)
        builder.get_object("project_uri_label").set_text(
            beautify_project_path(recent_project_item.get_uri_display()))
        builder.get_object("project_last_updated_label").set_text(
            beautify_last_updated_timestamp(recent_project_item.get_modified()))


# pylint: disable=too-many-instance-attributes
class GreeterPerspective(Perspective):
    """Pitivi's Welcome/Greeter perspective.

    Allows the user to create a new project or open an existing one.

    Attributes:
        app (Pitivi): The app.
    """

    def __init__(self, app):
        Perspective.__init__(self)

        self.app = app
        self.new_project_action = None
        self.open_project_action = None

        self.__topvbox = None
        self.__welcome_vbox = None
        self.__recent_projects_vbox = None
        self.__search_entry = None
        self.__recent_projects_labelbox = None
        self.__recent_projects_listbox = None
        self.__project_filter = self.__create_project_filter()
        self.__infobar = None
        self.__selection_button = None
        self.__actionbar = None
        self.__remove_projects_button = None
        self.__recent_items = None
        self.__cancel_button = None
        self.__new_project_button = None
        self.__open_project_button = None

        # Projects selected for removal.
        self.__selected_projects = []

        if app.getLatest():
            self.__show_newer_available_version()
        else:
            app.connect("version-info-received", self.__app_version_info_received_cb)

    def setup_ui(self):
        """Sets up the UI."""
        builder = Gtk.Builder()
        builder.add_from_file(os.path.join(get_ui_dir(), "greeter.ui"))

        self.toplevel_widget = builder.get_object("toplevel_vbox")

        self.__topvbox = builder.get_object("topvbox")
        self.__welcome_vbox = builder.get_object("welcome_vbox")
        self.__recent_projects_vbox = builder.get_object("recent_projects_vbox")

        self.__recent_projects_labelbox = builder.get_object("recent_projects_labelbox")

        self.__search_entry = builder.get_object("search_entry")
        self.__search_entry.connect("search-changed", self.__search_changed_cb)

        self.__recent_projects_listbox = builder.get_object("recent_projects_listbox")
        self.__recent_projects_listbox.set_selection_mode(Gtk.SelectionMode.NONE)
        self.__recent_projects_listbox.connect(
            "row_activated", self.__projects_row_activated_cb)

        self.__infobar = builder.get_object("infobar")
        fix_infobar(self.__infobar)
        self.__infobar.hide()
        self.__infobar.connect("response", self.__infobar_response_cb)

        self.__actionbar = builder.get_object("actionbar")
        self.__remove_projects_button = builder.get_object("remove_projects_button")
        self.__remove_projects_button.get_style_context().add_class("destructive-action")
        self.__remove_projects_button.connect("clicked", self.__remove_projects_button_cb)

        self.__setup_css()
        self.headerbar = self.__create_headerbar()
        self.__set_keyboard_shortcuts()

    def refresh(self):
        """Refreshes the perspective."""
        # Hide actionbar because we only want to show it during projects removal screen.
        self.__actionbar.hide()
        self.__remove_projects_button.set_sensitive(False)
        self.__selected_projects = []

        # Clear the currently displayed list of recent projects.
        for child in self.__recent_projects_listbox.get_children():
            self.__recent_projects_listbox.remove(child)

        self.__recent_items = [item for item in self.app.recent_manager.get_items()
                               if item.get_display_name().endswith(self.__project_filter)]

        # If there are recent projects, display them, else display welcome screen.
        if self.__recent_items:
            for item in self.__recent_items[:MAX_RECENT_PROJECTS]:
                recent_project_info = ProjectInfoRow(item)
                recent_project_info.select_button.connect(
                    "toggled", self.__project_selected_cb, recent_project_info)
                self.__recent_projects_listbox.add(recent_project_info)
                recent_project_info.show()

            child = self.__recent_projects_vbox
            self.__recent_projects_listbox.show()
        else:
            child = self.__welcome_vbox

        children = self.__topvbox.get_children()
        if children:
            current_child = children[0]
            if current_child == child:
                child = None
            else:
                self.__topvbox.remove(current_child)

        if child:
            self.__topvbox.pack_start(child, False, False, 0)

        if self.__recent_items:
            self.__search_entry.show()
            # We are assuming that the users name their projects meaningfully
            # and are sure of what project they want to search for. Once they
            # find the project and open it they don't want to come back to the
            # previous search results. So, we clear out the search entry before
            # the greeter is shown again.
            self.__search_entry.set_text("")
            self.__search_entry.grab_focus()

        self.__update_headerbar()

    def __setup_css(self):
        css_provider = Gtk.CssProvider()
        css_provider.load_from_data(GREETER_PERSPECTIVE_CSS.encode('UTF-8'))
        screen = Gdk.Screen.get_default()
        style_context = self.app.gui.get_style_context()
        style_context.add_provider_for_screen(screen, css_provider,
                                              Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)

    def __create_headerbar(self):
        headerbar = Gtk.HeaderBar()

        self.__new_project_button = Gtk.Button.new_with_label(_("New"))
        self.__new_project_button.set_tooltip_text(_("Create a new project"))
        self.__new_project_button.set_action_name("greeter.new-project")

        self.__open_project_button = Gtk.Button.new_with_label(_("Open…"))
        self.__open_project_button.set_tooltip_text(_("Open an existing project"))
        self.__open_project_button.set_action_name("greeter.open-project")

        self.__selection_button = Gtk.Button.new_from_icon_name("object-select-symbolic",
                                                                Gtk.IconSize.BUTTON)
        self.__selection_button.set_tooltip_text(_("Select projects for removal"))
        self.__selection_button.connect("clicked", self.__projects_removal_cb)

        self.__cancel_button = Gtk.Button.new_with_label(_("Cancel"))
        self.__cancel_button.set_tooltip_text(_("Return to project selection"))
        self.__cancel_button.connect("clicked", self.__cancel_projects_removal_cb)

        self.menu_button = self.__create_menu()

        headerbar.pack_start(self.__new_project_button)
        headerbar.pack_start(self.__open_project_button)
        headerbar.pack_end(self.menu_button)
        headerbar.pack_end(self.__selection_button)
        headerbar.pack_end(self.__cancel_button)
        headerbar.show()

        return headerbar

    def __update_headerbar(self):
        greeter = bool(self.__recent_items) and self.__search_entry.get_visible()
        projects_removal = bool(self.__recent_items) and not self.__search_entry.get_visible()

        self.headerbar.set_show_close_button(not projects_removal)
        self.headerbar.get_style_context().remove_class("selection-mode")
        self.__new_project_button.set_visible(not projects_removal)
        self.__open_project_button.set_visible(not projects_removal)
        self.menu_button.set_visible(not projects_removal)
        self.__cancel_button.set_visible(projects_removal)
        self.__selection_button.set_visible(greeter)

        if projects_removal:
            self.headerbar.set_title(_("Click an item to select"))
            self.headerbar.get_style_context().add_class("selection-mode")
        elif greeter:
            self.headerbar.set_title(_("Select a Project"))
        else:
            self.headerbar.set_title(_("Pitivi"))

    def __set_keyboard_shortcuts(self):
        group = Gio.SimpleActionGroup()
        self.toplevel_widget.insert_action_group("greeter", group)
        self.headerbar.insert_action_group("greeter", group)

        self.new_project_action = Gio.SimpleAction.new("new-project", None)
        self.new_project_action.connect("activate", self.__new_project_cb)
        group.add_action(self.new_project_action)
        self.app.shortcuts.add("greeter.new-project", ["<Primary>n"],
                               _("Create a new project"), group="win")

        self.open_project_action = Gio.SimpleAction.new("open-project", None)
        self.open_project_action.connect("activate", self.__open_project_cb)
        group.add_action(self.open_project_action)
        self.app.shortcuts.add("greeter.open-project", ["<Primary>o"],
                               _("Open a project"), group="win")

    @staticmethod
    def __create_project_filter():
        filter_ = []
        for asset in GES.list_assets(GES.Formatter):
            filter_.append(asset.get_meta(GES.META_FORMATTER_EXTENSION))
        return tuple(filter_)

    @staticmethod
    def __create_menu():
        builder = Gtk.Builder()
        builder.add_from_file(os.path.join(get_ui_dir(), "mainmenubutton.ui"))
        menu_button = builder.get_object("menubutton")
        # Menu options we want to display.
        visible_options = ["menu_shortcuts", "menu_help", "menu_about"]
        for widget in builder.get_object("menu").get_children():
            if Gtk.Buildable.get_name(widget) not in visible_options:
                widget.hide()
            else:
                visible_options.remove(Gtk.Buildable.get_name(widget))
        assert not visible_options
        return menu_button

    def __new_project_cb(self, unused_action, unused_param):
        self.app.project_manager.newBlankProject()

    def __open_project_cb(self, unused_action, unused_param):
        dialog = BrowseProjectsDialog(self.app)
        response = dialog.run()
        uri = dialog.get_uri()
        dialog.destroy()
        if response == Gtk.ResponseType.OK:
            self.app.project_manager.loadProject(uri)

    def __app_version_info_received_cb(self, app, unused_version_information):
        """Handles new version info."""
        if app.isLatest():
            # current version, don't show message
            return
        self.__show_newer_available_version()

    def __show_newer_available_version(self):
        latest_version = self.app.getLatest()

        if self.app.settings.lastCurrentVersion != latest_version:
            # new latest version, reset counter
            self.app.settings.lastCurrentVersion = latest_version
            self.app.settings.displayCounter = 0

        if self.app.settings.displayCounter >= 5:
            # current version info already showed 5 times, don't show again
            return

        # increment counter, create infobar and show info
        self.app.settings.displayCounter += 1
        text = _("Pitivi %s is available.") % latest_version
        label = Gtk.Label(label=text)
        self.__infobar.get_content_area().add(label)
        self.__infobar.set_message_type(Gtk.MessageType.INFO)
        self.__infobar.show_all()

    def __infobar_response_cb(self, unused_infobar, response_id):
        if response_id == Gtk.ResponseType.CLOSE:
            self.__infobar.hide()

    def __projects_row_activated_cb(self, unused_listbox, row):
        if row.select_button.get_visible():
            row.select_button.set_active(not row.select_button.get_active())
        else:
            self.app.project_manager.loadProject(row.uri)

    def __search_changed_cb(self, search_entry):
        search_hit = False
        search_text = search_entry.get_text().lower()
        for recent_project_item in self.__recent_projects_listbox.get_children():
            if search_text in recent_project_item.name.lower():
                recent_project_item.show()
                search_hit = True
            else:
                recent_project_item.hide()

        if search_hit:
            self.__recent_projects_labelbox.show()
            self.__recent_projects_listbox.show()
        else:
            self.__recent_projects_labelbox.hide()
            self.__recent_projects_listbox.hide()

    def __projects_removal_cb(self, unused_button):
        self.__search_entry.hide()
        self.__update_headerbar()
        self.__actionbar.show()
        for child in self.__recent_projects_listbox.get_children():
            child.select_button.show()

    def __cancel_projects_removal_cb(self, unused_button):
        self.refresh()

    def __project_selected_cb(self, check_button, project):
        if check_button.get_active():
            self.__selected_projects.append(project)
        else:
            self.__selected_projects.remove(project)

        self.__remove_projects_button.set_sensitive(bool(self.__selected_projects))

    def __remove_projects_button_cb(self, unused_button):
        for project in self.__selected_projects:
            self.app.recent_manager.remove_item(project.uri)
        self.refresh()
