# SPDX-FileCopyrightText: 2026 Valkyrie Profile 2 Translation Tools contributors
# SPDX-License-Identifier: GPL-3.0-only
import unittest
from unittest import mock

from tools.scripts import slz, slz_compress


_SAMPLES = [
    b"",
    b"AB",
    bytes(range(256)) * 12,
    b"\0" * 20000,
    b"ValkyrieProfile2!" * 300,
]


class MemoTests(unittest.TestCase):
    """``slz.decompress`` answers a repeated blob without decoding it again."""

    def setUp(self):
        slz.forget()
        self.addCleanup(slz.forget)

    def _blob(self, payload, mode=1):
        return slz_compress.compress(payload, mode=mode, cache_dir="")

    def test_round_trips_every_mode_with_the_memo_on(self):
        for payload in _SAMPLES:
            for mode in (1, 2):
                with self.subTest(size=len(payload), mode=mode):
                    self.assertEqual(
                        payload, slz.decompress(self._blob(payload, mode)))

    def test_a_repeat_does_not_decode_again(self):
        blob = self._blob(_SAMPLES[2])
        self.assertEqual(_SAMPLES[2], slz.decompress(blob))
        with mock.patch.object(slz, "_decompress",
                               side_effect=AssertionError("decoded again")):
            self.assertEqual(_SAMPLES[2], slz.decompress(blob))

    def test_a_repeat_hands_back_the_same_object(self):
        blob = self._blob(_SAMPLES[2])
        self.assertIs(slz.decompress(blob), slz.decompress(blob))

    def test_a_headerless_blob_is_keyed_by_its_mode_and_size(self):
        payload = _SAMPLES[4]
        body = self._blob(payload)[16:]
        self.assertEqual(payload, slz.decompress(body, 1, len(payload)))
        with mock.patch.object(slz, "_decompress",
                               return_value=b"asked again") as again:
            # A different claimed size is a different question, not a hit.
            self.assertEqual(b"asked again",
                             slz.decompress(body, 1, len(payload) - 2))
            again.assert_called_once()

    def test_bytearray_and_bytes_are_the_same_blob(self):
        blob = self._blob(_SAMPLES[3])
        self.assertEqual(_SAMPLES[3], slz.decompress(bytearray(blob)))
        with mock.patch.object(slz, "_decompress",
                               side_effect=AssertionError("decoded again")):
            self.assertEqual(_SAMPLES[3], slz.decompress(blob))

    def test_the_cap_evicts_least_recently_used_payloads(self):
        with mock.patch.object(slz, "_MEMO_LIMIT", 6000):
            for index in range(8):
                slz.decompress(self._blob(bytes([index]) * 1000))
            held = slz.memo_stats()
            self.assertLessEqual(held["bytes"], 6000)
            self.assertEqual(6, held["entries"])

    def test_a_payload_over_the_cap_is_not_kept(self):
        with mock.patch.object(slz, "_MEMO_LIMIT", 128):
            self.assertEqual(_SAMPLES[3],
                             slz.decompress(self._blob(_SAMPLES[3])))
            self.assertEqual(0, slz.memo_stats()["entries"])

    def test_the_memo_can_be_turned_off(self):
        blob = self._blob(_SAMPLES[2])
        with mock.patch.object(slz, "_MEMO_LIMIT", 0):
            self.assertEqual(_SAMPLES[2], slz.decompress(blob))
            self.assertEqual(0, slz.memo_stats()["entries"])

    def test_forget_releases_everything(self):
        slz.decompress(self._blob(_SAMPLES[2]))
        self.assertTrue(slz.memo_stats()["entries"])
        slz.forget()
        self.assertEqual({"entries": 0, "bytes": 0,
                          "limit": slz.memo_stats()["limit"]},
                         slz.memo_stats())


if __name__ == "__main__":
    unittest.main()
