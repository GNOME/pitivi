# -*- coding: utf-8 -*-
# Pitivi video editor
# Copyright (c) 2013, Alex Băluț <alexandru.balut@gmail.com>
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
from unittest import mock

from gi.repository import GES

from pitivi.utils.timeline import SELECT
from pitivi.utils.timeline import SELECT_ADD
from pitivi.utils.timeline import Selected
from pitivi.utils.timeline import Selection
from pitivi.utils.timeline import UNSELECT
from tests import common


class TestSelected(common.TestCase):

    def testBoolEvaluation(self):
        selected = Selected()
        self.assertFalse(selected)

        selected.selected = True
        self.assertTrue(selected)

        selected.selected = False
        self.assertFalse(selected)


class TestSelection(common.TestCase):

    def testBoolEvaluation(self):
        clip1 = mock.MagicMock()
        selection = Selection()
        self.assertFalse(selection)
        selection.setSelection([clip1], SELECT)
        self.assertTrue(selection)
        selection.setSelection([clip1], SELECT_ADD)
        self.assertTrue(selection)
        selection.setSelection([clip1], UNSELECT)
        self.assertFalse(selection)

    def testGetSingleClip(self):
        selection = Selection()
        clip1 = common.create_test_clip(GES.UriClip)
        clip2 = common.create_test_clip(GES.TitleClip)

        # Selection empty.
        self.assertIsNone(selection.getSingleClip())
        self.assertIsNone(selection.getSingleClip(GES.UriClip))
        self.assertIsNone(selection.getSingleClip(GES.TitleClip))

        selection.setSelection([clip1], SELECT)
        self.assertEqual(selection.getSingleClip(), clip1)
        self.assertEqual(selection.getSingleClip(GES.UriClip), clip1)
        self.assertIsNone(selection.getSingleClip(GES.TitleClip))

        selection.setSelection([clip2], SELECT)
        self.assertEqual(selection.getSingleClip(), clip2)
        self.assertIsNone(selection.getSingleClip(GES.UriClip))
        self.assertEqual(selection.getSingleClip(GES.TitleClip), clip2)

        selection.setSelection([clip1, clip2], SELECT)
        self.assertIsNone(selection.getSingleClip())
        self.assertIsNone(selection.getSingleClip(GES.UriClip))
        self.assertIsNone(selection.getSingleClip(GES.TitleClip))

    def test_can_group_ungroup(self):
        clip1 = common.create_test_clip(GES.UriClip)
        clip2 = common.create_test_clip(GES.UriClip)
        selection = Selection()
        self.assertFalse(selection)

        selection.setSelection([clip1], SELECT)
        self.assertFalse(selection.can_ungroup)
        self.assertFalse(selection.can_group)

        selection.setSelection([clip2], SELECT_ADD)
        self.assertTrue(selection.can_group)
        self.assertFalse(selection.can_ungroup)

        selection.setSelection([], SELECT)
        self.assertFalse(selection.can_group)
        self.assertFalse(selection.can_ungroup)
