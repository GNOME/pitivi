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
"""Dialog for browsing through projects to open an existing project."""
from gettext import gettext as _

from gi.repository import GES
from gi.repository import Gtk


# pylint: disable=too-few-public-methods
class BrowseProjectsDialog(Gtk.FileChooserDialog):
    """Displays the Gtk.FileChooserDialog for browsing projects.

    Attributes:
        app (Pitivi): The app.
    """

    def __init__(self, app):
        Gtk.FileChooserDialog.__init__(self)

        # Requesting project closure at this point in time prompts users about
        # unsaved changes (if any); much better than having ProjectManager
        # trigger this *after* the user already chose a new project to load...
        if not app.project_manager.closeRunningProject():
            return  # The user has not made a decision, don't do anything.

        self.set_title(_("Open File..."))
        self.set_transient_for(app.gui)
        self.set_action(Gtk.FileChooserAction.OPEN)

        self.add_buttons(_("Cancel"), Gtk.ResponseType.CANCEL,
                         _("Open"), Gtk.ResponseType.OK)
        self.set_default_response(Gtk.ResponseType.OK)
        self.set_select_multiple(False)
        # TODO: Remove this set_current_folder call when GTK bug 683999 is
        # fixed
        self.set_current_folder(app.settings.lastProjectFolder)
        formatter_assets = GES.list_assets(GES.Formatter)
        formatter_assets.sort(
            key=lambda x: - x.get_meta(GES.META_FORMATTER_RANK))
        for format_ in formatter_assets:
            filt = Gtk.FileFilter()
            filt.set_name(format_.get_meta(GES.META_DESCRIPTION))
            filt.add_pattern("*%s" %
                             format_.get_meta(GES.META_FORMATTER_EXTENSION))
            self.add_filter(filt)
        default = Gtk.FileFilter()
        default.set_name(_("All supported formats"))
        default.add_custom(Gtk.FileFilterFlags.URI, self.__can_load_uri, None)
        self.add_filter(default)

    # pylint: disable=bare-except
    @staticmethod
    def __can_load_uri(filterinfo, unused_uri):
        try:
            return GES.Formatter.can_load_uri(filterinfo.uri)
        except:
            return False
