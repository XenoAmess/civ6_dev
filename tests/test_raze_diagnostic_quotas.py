"""Keep the fixed sample cap across real pre/post Raze UI layouts."""
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path
from tools.diagnostic_quotas import bounded_quotas


class RazeDiagnosticQuotas(unittest.TestCase):
    def keys(self):
        root = ET.fromstring((Path(__file__).resolve().parents[1] / 'mod/Baiqi/Baiqi.modinfo').read_bytes())
        return [entry.findtext('Properties/LuaReplace') for entry in root.findall('InGameActions/ReplaceUIScript')] + ['UI/BaiqiExecutor.lua', 'Lua/BaiqiGameplay.lua']

    def test_actual_34_contexts_include_raze_without_increasing_sample_cap(self):
        keys = self.keys()
        self.assertEqual(len(keys), 34)
        quotas = bounded_quotas(keys, allocation='current181')
        self.assertEqual(set(quotas), set(keys))
        self.assertEqual((sum(quotas.values()), quotas['UI/BaiqiExecutor.lua'], quotas['UI/BaiqiRazeCity.lua']), (4096, 2016, 16))
        self.assertEqual((quotas['Lua/BaiqiGameplay.lua'], quotas['UI/BaiqiUnitFlagManager.lua']), (512, 384))

    def test_historical_32_and_33_allocations_retain_their_exact_quotas(self):
        keys = self.keys()
        keys.remove('UI/BaiqiRazeCity.lua')
        legacy33 = bounded_quotas(keys)
        current33 = bounded_quotas(keys, allocation='current140')
        keys.remove('UI/BaiqiWorldCrisisPopup.lua')
        legacy32 = bounded_quotas(keys)
        self.assertEqual([sum(q.values()) for q in (legacy32, legacy33, current33)], [4096] * 3)
        self.assertEqual([q['UI/BaiqiExecutor.lua'] for q in (legacy32, legacy33, current33)], [2048, 2032, 2032])
        self.assertEqual(legacy32['Lua/BaiqiGameplay.lua'], 128)

    def test_unknown_layout_duplicate_missing_context_and_wrong_profile_are_rejected(self):
        keys = self.keys()
        renamed = [k if k != 'UI/BaiqiRazeCity.lua' else 'UI/Unknown.lua' for k in keys]
        for bad, profile in ((renamed, 'current181'), (keys + ['UI/Unknown.lua'], 'current181'), (keys[:-1] + [keys[0]], 'current181'), (keys, 'current140'), (keys[:-1], 'current181')):
            with self.subTest(profile=profile, keys=bad), self.assertRaises((ValueError, TypeError)):
                bounded_quotas(bad, allocation=profile)


if __name__ == '__main__':
    unittest.main()
