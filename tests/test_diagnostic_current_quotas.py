from pathlib import Path
import unittest
import xml.etree.ElementTree as ET
from lupa.lua51 import LuaRuntime

from tools.diagnostic_quotas import bounded_quotas, OVERRIDES

ROOT = Path(__file__).resolve().parents[1]


class CurrentQuotaTests(unittest.TestCase):
    def setUp(self):
        info = ET.fromstring((ROOT/'mod/Baiqi/Baiqi.modinfo').read_bytes())
        self.keys = [e.findtext('Properties/LuaReplace') for e in info.findall('InGameActions/ReplaceUIScript')]
        self.keys += ['UI/BaiqiExecutor.lua', 'Lua/BaiqiGameplay.lua']

    def test_exact_transfer_keeps_default_historical_layout_and_global_cap(self):
        original = dict(OVERRIDES)
        legacy = bounded_quotas(self.keys)
        current = bounded_quotas(self.keys, allocation='current140')
        differences = {k: current[k] - legacy[k] for k in self.keys if current[k] != legacy[k]}
        self.assertEqual(differences, {'UI/BaiqiUnitFlagManager.lua': -384, 'Lua/BaiqiGameplay.lua': 384})
        self.assertEqual((sum(current.values()), current['UI/BaiqiExecutor.lua']), (4096, 2032))
        self.assertEqual((current['Lua/BaiqiGameplay.lua'], current['UI/BaiqiUnitFlagManager.lua']), (512, 384))
        self.assertEqual(bounded_quotas(self.keys), legacy)
        old = bounded_quotas([k for k in self.keys if k != 'UI/BaiqiWorldCrisisPopup.lua'])
        self.assertEqual((len(old), sum(old.values()), old['UI/BaiqiExecutor.lua']), (32, 4096, 2048))
        self.assertEqual(OVERRIDES, original)

    def test_current_profile_rejects_old_layout_and_unknown_profiles(self):
        with self.assertRaises(ValueError):
            bounded_quotas([k for k in self.keys if k != 'UI/BaiqiWorldCrisisPopup.lua'], allocation='current140')
        for value in ('current139', 'unknown', None, False):
            with self.subTest(value=value), self.assertRaises(ValueError):
                bounded_quotas(self.keys, allocation=value)

    def test_actual_contexts_retain_observed_load_under_unchanged_global_limit(self):
        quota = bounded_quotas(self.keys, allocation='current140')
        lua = LuaRuntime(unpack_returned_tuples=True)
        for stem, name in [('diagnostic_profile', 'NewProfile'), ('diagnostic_owned_roots', 'NewRoots'),
                           ('diagnostic_queries', 'NewCounter'), ('diagnostic_write_leaves', 'NewLeaves'),
                           ('diagnostic_context', 'NewContext')]:
            lua.globals()[name] = lua.execute((ROOT/f'tools/lua/{stem}.lua').read_text(encoding='utf-8'))
        lua.globals().CoreQuota = quota['Lua/BaiqiGameplay.lua']
        lua.globals().FlagQuota = quota['UI/BaiqiUnitFlagManager.lua']
        lua.execute('''
          local clock=1;local env={AggregateZero=true,ExposedMembers={},Game={GetCurrentGameTurn=function()return 90 end},
            Automation={GetTime=function()return clock end},Events={PlayerTurnActivated={Add=function()end,Remove=function()end}}}
          env.SampleQuota=CoreQuota;local core=NewContext('Lua/BaiqiGameplay.lua',env,NewProfile,NewRoots,NewCounter,NewLeaves)
          env.SampleQuota=FlagQuota;local flag=NewContext('UI/BaiqiUnitFlagManager.lua',env,NewProfile,NewRoots,NewCounter,NewLeaves)
          core:SetEnabled(true);flag:SetEnabled(true)
          local c=core:Wrap('core',function()clock=clock+0.001 end)
          local f=flag:Wrap('flag',function()clock=clock+0.001 end)
          for i=1,135 do c()end;for i=1,137 do f()end
          assert(#core.profile.samples==135 and core.profile.dropped==0)
          assert(#flag.profile.samples==137 and flag.profile.dropped==0)
          for i=136,513 do c()end
          assert(#core.profile.samples==512 and core.profile.dropped==1)
        ''')


if __name__ == '__main__':
    unittest.main()
