# -*- coding: utf-8 -*-
# Pitivi Developer Console
# Copyright (c) 2017-2018, Fabian Orccon <cfoch.fabian@gmail.com>
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
"""The developer console widget:"""
from gi.repository import Gdk
from gi.repository import GLib
from gi.repository import Gtk
from utils import ConsoleBuffer


class ConsoleWidget(Gtk.ScrolledWindow):
    """An emulated Python console.

    The console can be used to access an app, window, or anything through the
    provided namespace. It works redirecting stdout and stderr to a
    GtkTextBuffer. This class is (and should be) independent of the application
    it is integrated with.
    """

    def __init__(self, namespace):
        Gtk.ScrolledWindow.__init__(self)
        self._view = Gtk.TextView()
        buf = ConsoleBuffer(namespace)
        self._view.set_buffer(buf)
        self._view.set_editable(True)
        self.add(self._view)

        self._view.connect("key-press-event", self.__key_press_event_cb)
        buf.connect("mark-set", self.__mark_set_cb)
        buf.connect("insert-text", self.__insert_text_cb)

    def scroll_to_end(self):
        """Scrolls the view to the end."""
        end_iter = self._view.get_buffer().get_end_iter()
        self._view.scroll_to_iter(end_iter, within_margin=0.0, use_align=False,
                                  xalign=0, yalign=0)
        return False

    @classmethod
    def __key_press_event_cb(cls, view, event):
        if event.keyval == Gdk.KEY_Return:
            view.get_buffer().process_command_line()
            return True
        if event.keyval in (Gdk.KEY_KP_Down, Gdk.KEY_Down):
            return True
        if event.keyval in (Gdk.KEY_KP_Up, Gdk.KEY_Up):
            return True
        if event.keyval in (Gdk.KEY_KP_Left, Gdk.KEY_Left, Gdk.KEY_BackSpace):
            return view.get_buffer().is_cursor_at_start()
        return False

    def __mark_set_cb(self, buf, unused_iter, unused_name):
        self._view.set_editable(buf.is_cursor_before_last_prompt())

    def __insert_text_cb(self, buf, unused_iter, unused_text, unused_len):
        GLib.idle_add(self.scroll_to_end)
