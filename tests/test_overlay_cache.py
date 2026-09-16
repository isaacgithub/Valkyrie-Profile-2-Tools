# SPDX-FileCopyrightText: 2026 Valkyrie Profile 2 Translation Tools contributors
# SPDX-License-Identifier: GPL-3.0-only
import os
import shutil
import tempfile
import unittest
from unittest import mock

from tools.cheat_patcher import slz, slz3, slz12
from tools.scripts import slz_cache


_SAMPLE = (b"Lorem ipsum dolor sit amet, consectetur adipiscing elit. "
           b"aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa "
           b"Sed do eiusmod tempor incididunt ut labore et dolore.")
_SAMPLE += b" " * (len(_SAMPLE) % 2)          # mode 3 encodes 16-bit units


class OverlayCacheTests(unittest.TestCase):
    """The overlay compressors answer from a store without changing bytes."""

    def setUp(self):
        self.store = tempfile.mkdtemp(prefix="vp2-overlay-cache-")
        patch = mock.patch.dict(
            os.environ, {"VP2_OVERLAY_CACHE": self.store})
        patch.start()
        self.addCleanup(patch.stop)
        self.addCleanup(shutil.rmtree, self.store, ignore_errors=True)

    def _stored(self):
        return sum(len(names) for _root, _dirs, names in os.walk(self.store))

    def test_mode_three_hit_matches_the_uncached_encoder(self):
        expected = slz3._compress_uncached(_SAMPLE, 0, slz3.MAX_CHAIN)
        first = slz3.compress(_SAMPLE)
        second = slz3.compress(_SAMPLE)
        self.assertEqual(expected, first)
        self.assertEqual(expected, second)
        self.assertEqual(_SAMPLE, slz.decompress(second))
        self.assertEqual(1, self._stored())

    def test_modes_one_and_two_hit_matches_the_uncached_encoder(self):
        for mode in (1, 2):
            with self.subTest(mode=mode):
                expected = slz12._compress_uncached(_SAMPLE, mode, 0)
                self.assertEqual(expected, slz12.compress(_SAMPLE, mode))
                self.assertEqual(expected, slz12.compress(_SAMPLE, mode))
                self.assertEqual(_SAMPLE, slz.decompress(expected))

    def test_second_call_does_not_run_the_encoder(self):
        slz3.compress(_SAMPLE)
        with mock.patch.object(slz3, "compress_body",
                               side_effect=AssertionError("encoded again")):
            self.assertEqual(_SAMPLE, slz.decompress(slz3.compress(_SAMPLE)))

    def test_parameters_are_part_of_the_key(self):
        slz3.compress(_SAMPLE, next_offset=0)
        slz3.compress(_SAMPLE, next_offset=64)
        slz12.compress(_SAMPLE, 1)
        slz12.compress(_SAMPLE, 2)
        self.assertEqual(4, self._stored())

    def test_mode_three_and_mode_one_do_not_share_a_key(self):
        self.assertNotEqual(
            slz_cache.name("slz3-v1", _SAMPLE, 0, slz3.MAX_CHAIN),
            slz_cache.name("slz12-v1", _SAMPLE, 1, 0))

    def test_store_can_be_turned_off(self):
        with mock.patch.dict(os.environ, {"VP2_OVERLAY_CACHE": "0"}):
            self.assertEqual(
                slz3._compress_uncached(_SAMPLE, 0, slz3.MAX_CHAIN),
                slz3.compress(_SAMPLE))
        self.assertEqual(0, self._stored())

    def test_a_refused_input_stores_nothing(self):
        with self.assertRaisesRegex(ValueError, "odd"):
            slz3.compress(b"odd")
        self.assertEqual(0, self._stored())


class StoreTests(unittest.TestCase):
    """The store itself."""

    def setUp(self):
        self.store = tempfile.mkdtemp(prefix="vp2-store-")
        self.seed = tempfile.mkdtemp(prefix="vp2-seed-")
        self.addCleanup(shutil.rmtree, self.store, ignore_errors=True)
        self.addCleanup(shutil.rmtree, self.seed, ignore_errors=True)

    def test_a_seed_hit_is_not_copied_into_the_store(self):
        key = slz_cache.name("t", b"payload", 1)
        slz_cache.write(self.seed, key, b"from-the-seed")
        produced = slz_cache.cached(
            self.store, key, lambda: b"fresh", seeds=(self.seed,))
        self.assertEqual(b"from-the-seed", produced)
        self.assertIsNone(slz_cache.read(self.store, key))

    def test_a_miss_is_produced_once_and_kept(self):
        key = slz_cache.name("t", b"payload", 1)
        calls = []

        def produce():
            calls.append(1)
            return b"made"

        self.assertEqual(b"made", slz_cache.cached(self.store, key, produce))
        self.assertEqual(b"made", slz_cache.cached(self.store, key, produce))
        self.assertEqual(1, len(calls))

    def test_resolve_prefers_the_caller_then_the_environment(self):
        with mock.patch.dict(os.environ, {"VP2_TEST_STORE": "from-env"}):
            self.assertEqual(
                "explicit",
                slz_cache.resolve("explicit", "fallback", "VP2_TEST_STORE"))
            self.assertEqual(
                "from-env",
                slz_cache.resolve(None, "fallback", "VP2_TEST_STORE"))
        with mock.patch.dict(os.environ, {"VP2_TEST_STORE": "0"}):
            self.assertEqual(
                "", slz_cache.resolve(None, "fallback", "VP2_TEST_STORE"))
        os.environ.pop("VP2_TEST_STORE", None)
        self.assertEqual(
            "fallback", slz_cache.resolve(None, "fallback", "VP2_TEST_STORE"))


if __name__ == "__main__":
    unittest.main()
