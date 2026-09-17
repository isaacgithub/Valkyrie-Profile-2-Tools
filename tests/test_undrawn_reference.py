"""A scene's reference sheet lists only the lines that can appear there."""
import csv
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from tools.scripts import undrawn_records, translation_layout  # noqa: E402


NAMES = ("Lwyn", "Jessica", "Arcana", "Sophalla")
FIELDS = ("kind", "scene", "scene_line", "resource", "message_id",
          "message_index", "script_offset", "voice_scene", "voice_slot",
          "audio_id", "speaker", "original_en", "original_jp", "translated",
          "details", "notes")


CAST = ("Dylan", "Brahms", "Hrist")
ITEMS = ("Ghoul Powder", "Antique Pendant", "Ghoul Powder", "Dragon Orb")

STORY = {"join": {"8": frozenset({"Dylan", "Hrist"}),
                  "9": frozenset({"Brahms"})},
         "item": {"8": frozenset({"Ghoul Powder", "Antique Pendant"}),
                  "9": frozenset({"Dragon Orb"})}}


def _rows(resource):
    rows = []

    def add(message_id, english, speaker=""):
        row = {field: "" for field in FIELDS}
        row.update(kind="scene", resource=resource, message_id=str(message_id),
                   speaker=speaker, original_en=english)
        rows.append(row)

    return rows, add


def _records():
    rows, add = _rows("7")

    for offset, name in enumerate(NAMES):
        add(96 + offset, "I will fight.", speaker=name)
    for number, english in enumerate((
            "A light warrior's soul emanates from the sword.",
            "A heavy warrior's soul emanates from the sword.",
            "An archer's soul emanates from the bow.",
            "A sorcerer's soul emanates from the staff.",
            "Perform materialization?", "Yes", "No",
            "Materialization is impossible without Silmeria...",
            "An Area Name"), start=100):
        add(number, english)
    for offset, name in enumerate(NAMES):
        add(200 + offset, f"{name} <PART> has joined the party.")
        add(300 + offset, name)
    return rows


def _story_records():
    rows, add = _rows("9")
    add(1, "EVENTíMAP")
    add(2, "The orb is here with us.", speaker="Brahms")
    for offset, item in enumerate(ITEMS):
        add(10 + offset, f"Acquired <PART> {item}")
    add(20, "Acquired <PART> Elixir")
    for offset, name in enumerate(CAST):
        add(100 + offset, f"{name} <PART> has joined the party.")
    return rows


TABLE = {"weapon": {"7": {"Arcana", "Sophalla"}},
         "weapon_type": {"7": "Archer"},
         "fallback": {"Jessica"},
         "release": {"8": {"Lwyn"}}}


class ReferenceSheetTests(unittest.TestCase):

    def _listed(self, resource, records):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / f"resource-{resource:04d}-scenes.csv"
            target = Path(directory) / f"scene-{resource:04d}.csv"
            with open(source, "w", encoding="utf-8", newline="") as handle:
                writer = csv.DictWriter(handle, fieldnames=FIELDS)
                writer.writeheader()
                writer.writerows(records)
            count = translation_layout._copy_reference_rows(
                source, target, translation_layout.SCENE_REFERENCE_FIELDS,
                lambda rows: undrawn_records.hidden_message_ids(
                    rows, TABLE, STORY))
            with open(target, encoding="utf-8", newline="") as handle:
                listed = [row["message_id"] for row in csv.DictReader(handle)]
        self.assertEqual(count, len(listed))
        return sorted(listed, key=int)

    def test_lines_that_cannot_appear_at_a_weapon_location_are_left_out(self):
        self.assertEqual(self._listed(7, _records()), [
            "97", "98", "99",                  # Jessica, Arcana, Sophalla
            "102",                             # the bow
            "104", "105", "106", "107",        # prompt, Yes, No, refusal
            "108",                             # the area name
            "201", "202", "203",               # joined the party
            "301", "302", "303",               # Jessica, Arcana, Sophalla
        ])

    def test_a_main_story_scene_lists_only_its_own_join_and_item(self):
        self.assertEqual(self._listed(9, _story_records()), [
            "2",                               # the dialogue
            "13",                              # Dragon Orb, acquired here
            "20",                              # an ordinary treasure
            "101",                             # Brahms, who joins here
        ])


if __name__ == "__main__":
    unittest.main()
