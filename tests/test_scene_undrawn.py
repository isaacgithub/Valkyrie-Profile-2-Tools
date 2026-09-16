"""Reclaiming the records a scene never draws."""

import os
import sys
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from tools.scripts import vp2_cutscene_subtitles  # noqa: F401  (import order)
from tools.scripts import scene_text

NEWLINE = chr(10)


class PlaceholderTests(unittest.TestCase):
    def test_every_marker_the_english_has_survives(self):
        english = ("One <PART> two." + NEWLINE + "---" + NEWLINE
                   + "Three <PART> four.")
        held = scene_text.undrawn_placeholder(english)
        for marker in ("<PART>", "---"):
            self.assertEqual(english.count(marker), held.count(marker))
        self.assertNotIn("two", held)
        self.assertLess(len(held), len(english))

    def test_a_blank_run_stays_blank(self):
        self.assertEqual(" - <PART>", scene_text.undrawn_placeholder("Words <PART>"))

    def test_the_mark_is_a_letter_the_record_itself_draws(self):
        self.assertEqual("i", scene_text.undrawn_mark("Is it my turn now?"))
        self.assertIsNone(scene_text.undrawn_mark("123"))


class ReclaimTests(unittest.TestCase):
    def rows(self):
        return [
            {"resource": "39", "message_id": "1",
             "original_en": "ERROR!!(v190)", "translated": "", "speaker": ""},
            {"resource": "39", "message_id": "2",
             "original_en": "Real line.", "translated": "", "speaker": ""},
            {"resource": "39", "message_id": "3",
             "original_en": "Authored.", "translated": "escrito", "speaker": ""},
        ]

    def test_debug_records_are_reclaimed_and_nothing_else(self):
        rows = self.rows()
        _rows, reclaimed = scene_text.reclaim_undrawn_rows(rows)
        self.assertEqual(1, reclaimed)
        self.assertIn("e", rows[0]["translated"])
        self.assertEqual("", rows[1]["translated"])
        self.assertEqual("escrito", rows[2]["translated"])


if __name__ == "__main__":
    unittest.main()
