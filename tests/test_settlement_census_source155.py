from pathlib import Path
import hashlib
import tempfile
import unittest

from tools.build_settlement_census_mod import transform, restore_release, build, EDITS
from tests import test_build_settlement_census as existing

ROOT = Path(__file__).resolve().parents[1]


class CensusSource155ConsumerTests(existing.SettlementCensusTransformTests):
    def setUp(self):
        self.raw = (ROOT / 'mod/Baiqi/Lua/BaiqiController.lua').read_text(encoding='utf-8')
        self.text, self.prefix = transform(self.raw, source_version=155)


class CensusVersionTests(unittest.TestCase):
    def source(self):
        return (ROOT / 'mod/Baiqi/Lua/BaiqiController.lua').read_text(encoding='utf-8')

    def test_legacy_prefix_and_edit_rules_keep_frozen_bytes(self):
        _, prefix = transform(self.source())
        self.assertEqual(hashlib.sha256(prefix.encode()).hexdigest(),
                         'db89de7172e7723f792b87c0d47c02bb4611dd67c336410db639f4a6899fb52c')
        self.assertEqual(hashlib.sha256(repr(EDITS).encode()).hexdigest(),
                         'e4bf739447425b7c7b3486d74c1db168e87fc606138c3aa8cae4180dcbfe254f')

    def test_explicit_142_matches_default_and_source155_recovers_exactly(self):
        raw = self.source()
        self.assertEqual(transform(raw, source_version=142), transform(raw))
        text, prefix = transform(raw, source_version=155)
        self.assertIn('natural source155 settlement census', prefix)
        self.assertNotIn('natural source142 settlement census', prefix)
        self.assertEqual(restore_release(text, prefix), raw)

    def test_unknown_versions_and_nonexact_types_are_rejected(self):
        class IntSubclass(int):
            pass
        for value in (True, 155.0, '155', None, 141, 154, 164, IntSubclass(155)):
            with self.subTest(value=value), self.assertRaises(ValueError):
                transform(self.source(), source_version=value)

    def test_current_build_has_actual_version_and_unchanged_inventory(self):
        with tempfile.TemporaryDirectory() as folder:
            output = Path(folder) / 'prepared'
            data = build(output)
            self.assertEqual(data['source_version'], 163)
            self.assertEqual(data['mode'], 'baiqi163-settlement-census-v1')
            self.assertEqual(data['changed_files'], ['Lua/BaiqiController.lua'])
            self.assertEqual(data['census_capacity'], 256)
            self.assertTrue((output / 'Baiqi-settlement163-census.zip').is_file())
            self.assertEqual(data['files'], len(data['source_hashes']))
            self.assertEqual(data['Native_pressure_status'], 'UNVERIFIED')
            self.assertTrue(data['release_recovers_exactly'])
