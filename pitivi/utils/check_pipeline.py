# -*- coding: utf-8 -*-
# Pitivi video editor
# Copyright (c) 2019, Thibault Saunier <tsaunier@igalia.com>
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
"""
Simple app to check if a GStreamer pipeline can run.
"""
import os
import sys

import gi

gi.require_version("Gst", "1.0")

from gi.repository import Gst  # pylint: disable-msg=wrong-import-position
from gi.repository import GLib  # pylint: disable-msg=wrong-import-position


def pipeline_message_cb(_, msg, pipeline):
    """GStreamer bus message handler."""
    if msg.type == Gst.MessageType.ASYNC_DONE:
        print("pipeline successfully PAUSED")
        pipeline.set_state(Gst.State.NULL)
        sys.exit(0)
    elif msg.type == Gst.MessageType.ERROR:
        # The pipeline cannot be set to PAUSED.
        error, detail = msg.parse_error()
        print("Pipeline failed: %s, %s" % (error, detail), file=sys.stderr)
        pipeline.set_state(Gst.State.NULL)
        sys.exit(1)


def timeout_cb(*args, **kwargs):
    """Exit on timeout."""
    print("Pipeline timed out", file=sys.stderr)
    sys.exit(1)


def main():
    """Main function of the small app."""
    os.environ["G_DEBUG"] = "fatal-criticals"
    Gst.init(None)
    pipeline = Gst.parse_launch(sys.argv[1])
    bus = pipeline.get_bus()
    bus.add_signal_watch()
    bus.connect("message", pipeline_message_cb, pipeline)
    res = pipeline.set_state(Gst.State.PAUSED)
    assert res == Gst.StateChangeReturn.ASYNC

    GLib.timeout_add_seconds(10, timeout_cb)
    GLib.MainLoop.new(None, True).run()


if __name__ == "__main__":
    main()
