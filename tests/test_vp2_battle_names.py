# SPDX-FileCopyrightText: 2026 Valkyrie Profile 2 Translation Tools contributors
# SPDX-License-Identifier: GPL-3.0-only

import struct
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from tools.scripts import overlay_edits
from tools.scripts import vp2_battle_names as names
from tools.scripts import vp2_build


class BattleNameEncodingTests(unittest.TestCase):
    def test_misc_keys_use_uppercase_hex_table_indices(self):
        self.assertEqual("battle_name_0A", names.key(10))
        self.assertEqual("battle_name_0D", names.key(13))
        self.assertEqual("battle_name_37", names.key(55))

    def test_letters_are_zero_based_and_input_is_uppercased(self):
        encoded = names.encode_name("Valquiria")
        self.assertEqual(bytes.fromhex(
            "15 00 0b 10 14 08 11 08 00 ff"), encoded[:10])
        self.assertEqual(b"\0" * 10, encoded[10:])

    def test_hyphen_has_its_observed_table_code(self):
        self.assertEqual(bytes.fromhex("12 07 00 fe 0a 0e 0d ff"),
                         names.encode_name("SHA-KON")[:8])

    def test_only_the_battle_atlas_characters_are_accepted(self):
        for value in ("VALQUÍRIA", "DOG ARMITAGE", "FREYA!"):
            with self.subTest(value=value):
                with self.assertRaisesRegex(ValueError, "A-Z or hyphen"):
                    names.encode_name(value)

    def test_the_terminator_must_fit_the_twenty_byte_field(self):
        self.assertEqual(20, len(names.encode_name("A" * 19)))
        with self.assertRaisesRegex(ValueError, "at most 19"):
            names.encode_name("A" * 20)

    def test_a_misspelled_feature_key_is_not_silently_ignored(self):
        with self.assertRaisesRegex(ValueError, "unknown.*key"):
            names.translations({"battle_name_99": "Nobody"})


def usa_overlay():
    size = names.TABLE_OFFSET + len(names.ORIGINAL_NAMES) * names.RECORD_SIZE
    output = bytearray(size)
    struct.pack_into("<I", output, 8, overlay_edits.LOAD_ADDRESS)
    for index, original in enumerate(names.ORIGINAL_NAMES):
        start = names.TABLE_OFFSET + index * names.RECORD_SIZE
        output[start:start + names.NAME_CAPACITY] = names.encode_name(original)
        output[start + names.NAME_CAPACITY:start + names.RECORD_SIZE] = b"META"
    return bytes(output)


class BattleNameEditTests(unittest.TestCase):
    def test_one_misc_value_changes_only_its_name_field(self):
        original = usa_overlay()
        edits = names.edits({"battle_name_0A": "Valquiria"})
        patched, changed = overlay_edits.edit_output(original, edits)
        start = names.TABLE_OFFSET + 10 * names.RECORD_SIZE
        expected = bytearray(original)
        expected[start:start + names.NAME_CAPACITY] = names.encode_name(
            "VALQUIRIA")
        self.assertEqual(bytes(expected), patched)
        self.assertEqual(7, changed)
        self.assertEqual(b"META", patched[start + names.NAME_CAPACITY:
                                           start + names.RECORD_SIZE])

    def test_applying_the_same_name_twice_is_harmless(self):
        edits = names.edits({"battle_name_0A": "Valquiria"})
        patched, _ = overlay_edits.edit_output(usa_overlay(), edits)
        again, changed = overlay_edits.edit_output(patched, edits)
        self.assertEqual(patched, again)
        self.assertEqual(0, changed)

    def test_the_build_reads_battle_names_from_misc(self):
        with tempfile.TemporaryDirectory() as folder:
            misc = Path(folder, "misc.csv")
            misc.write_text(
                "key,translated,notes\n"
                "battle_name_0A,Valquiria,VALKYRIE\n",
                encoding="utf-8")
            row = {"kind": "misc", "resource": "1781",
                   "sheet": str(misc)}
            self.assertEqual({10: "VALQUIRIA"},
                             vp2_build.battle_name_translations([row]))
            edits = vp2_build.battle_overlay_edits([row])
            self.assertEqual(1, len(edits))
            self.assertEqual(names.TABLE_OFFSET + 10 * names.RECORD_SIZE,
                             edits[0].offset)


if __name__ == "__main__":
    unittest.main()
