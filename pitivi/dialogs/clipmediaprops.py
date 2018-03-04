# -*- coding: utf-8 -*-
# Pitivi video editor
# Copyright (c) 2011, Parthasarathi Susarla <partha@collabora.co.uk>
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
# License along with this program; if not, see <http://www.gnu.org/licenses/>.
import os
from gettext import gettext as _

from gi.repository import Gdk
from gi.repository import Gst
from gi.repository import Gtk

from pitivi.configure import get_ui_dir
from pitivi.utils.ui import audio_channels
from pitivi.utils.ui import audio_rates
from pitivi.utils.ui import frame_rates
from pitivi.utils.ui import get_value_from_model
from pitivi.utils.ui import pixel_aspect_ratios


class ClipMediaPropsDialog(object):
    """Displays the properties of an asset.

    Allows applying them to the project.

    Attributes:
        project (Project): The project.
        asset (GES.UriClipAsset): The displayed asset.
    """

    def __init__(self, project, asset):
        self.project = project
        info = asset.get_info()
        self.audio_streams = info.get_audio_streams()
        self.video_streams = info.get_video_streams()
        self.has_audio = False
        self.has_video = False
        self.is_image = False

        builder = Gtk.Builder()
        builder.add_from_file(os.path.join(get_ui_dir(), "clipmediaprops.ui"))
        builder.connect_signals(self)
        self.dialog = builder.get_object("Import Settings")
        # Checkbuttons (with their own labels) in the first table column:
        self.size_checkbutton = builder.get_object("size_checkbutton")
        self.framerate_checkbutton = builder.get_object(
            "framerate_checkbutton")
        self.PAR_checkbutton = builder.get_object("PAR_checkbutton")
        self.channels_checkbutton = builder.get_object("channels_checkbutton")
        self.samplerate_checkbutton = builder.get_object("samplerate_checkbtn")
        # These labels are in a separate table col on the right of checkboxes:
        self.channels = builder.get_object("channels")
        self.size_height = builder.get_object("size_height")
        self.size_width = builder.get_object("size_width")
        self.frame_rate = builder.get_object("frame_rate")
        self.aspect_ratio = builder.get_object("aspect_ratio")
        self.sample_rate = builder.get_object("sample_rate")
        # Various other layout widgets
        self.frame1 = builder.get_object("frame1")
        self.frame2 = builder.get_object("frame2")
        self.hbox2 = builder.get_object("hbox2")
        self.hbox3 = builder.get_object("hbox3")
        self.video_header_label = builder.get_object("label2")

    def run(self):
        """Sets up widgets and run the dialog."""
        # TODO: in "onApplyButtonClicked", we only use the first stream...
        # If we have multiple audio or video streams, we should reflect that
        # in the UI, instead of acting as if there was only one. But that means
        # dynamically creating checkboxes and labels in a table and such.
        for stream in self.audio_streams:
            self.channels.set_text(
                get_value_from_model(audio_channels, stream.get_channels()))
            self.sample_rate.set_text(
                get_value_from_model(audio_rates, stream.get_sample_rate()))
            self.has_audio = True
            break

        for stream in self.video_streams:
            self.size_width.set_text(str(int(stream.get_square_width())))
            self.size_height.set_text(str(stream.get_height()))
            self.is_image = stream.is_image()
            if not self.is_image:
                # When gst returns a crazy framerate such as 0/1, that either
                # means it couldn't determine it, or it is a variable framerate
                framerate_num = stream.get_framerate_num()
                framerate_denom = stream.get_framerate_denom()
                if framerate_num != 0 and framerate_denom != 0:
                    self.frame_rate.set_text(
                        get_value_from_model(frame_rates,
                            Gst.Fraction(framerate_num, framerate_denom)
                        ))
                    if (framerate_num / framerate_denom) > 500:
                        # Sometimes you have "broken" 1000fps clips (WebM files
                        # from YouTube, for example), but it could also be a
                        # real framerate, so just uncheck instead of disabling:
                        self.framerate_checkbutton.set_active(False)
                else:
                    foo = str(framerate_num) + "/" + str(framerate_denom)
                    # Translators: a label showing an invalid framerate value
                    self.frame_rate.set_text(_("invalid (%s fps)") % foo)
                    self.framerate_checkbutton.set_active(False)
                    # For consistency, insensitize the checkbox AND value
                    # labels
                    self.framerate_checkbutton.set_sensitive(False)
                    self.frame_rate.set_sensitive(False)

                # Aspect ratio (probably?) doesn't need such a check:
                self.aspect_ratio.set_text(
                    get_value_from_model(pixel_aspect_ratios, Gst.Fraction(
                        stream.get_par_num(),
                        stream.get_par_denom())))

            self.has_video = True
            break

        if not self.has_video:
            self.frame1.hide()
        if not self.has_audio:
            self.frame2.hide()
        if self.is_image:
            self.hbox2.hide()
            self.hbox3.hide()
            self.video_header_label.set_markup("<b>" + _("Image:") + "</b>")

        self.dialog.connect("key-press-event", self._keyPressCb)
        self.dialog.connect("response", self.__response_cb)
        self.dialog.run()

    def _apply(self):
        """Applies the widgets values to the project."""
        project = self.project
        if self.has_video:
            # This also handles the case where the video is a still image
            video = self.video_streams[0]
            if self.size_checkbutton.get_active():
                project.videowidth = video.get_square_width()
                project.videoheight = video.get_height()
            if self.framerate_checkbutton.get_active() and not self.is_image:
                project.videorate = Gst.Fraction(video.get_framerate_num(),
                                                 video.get_framerate_denom())
        if self.has_audio:
            audio = self.audio_streams[0]
            if self.channels_checkbutton.get_active():
                project.audiochannels = audio.get_channels()
            if self.samplerate_checkbutton.get_active():
                project.audiorate = audio.get_sample_rate()

    def __response_cb(self, unused_dialog, response_id):
        if response_id == 1:
            self._apply()
        self.dialog.destroy()

    def _keyPressCb(self, unused_widget, event):
        if event.keyval in (Gdk.KEY_Escape, Gdk.KEY_Q, Gdk.KEY_q):
            self.dialog.destroy()
        return True
