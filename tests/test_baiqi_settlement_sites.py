"""Real settlement-hint producer: ranking, reservations and bounded city reads."""
from pathlib import Path
import unittest
from lupa.lua53 import LuaRuntime

ROOT = Path(__file__).resolve().parents[1]


class SettlementSiteTests(unittest.TestCase):
    def setUp(self):
        self.lua = LuaRuntime(unpack_returned_tuples=True)
        for name in ('tests/lua/mock_world.lua', 'tests/lua/mock_movement.lua',
                     'tests/lua/mock_path_ranking.lua', 'mod/Baiqi/Lua/BaiqiConfig.lua',
                     'mod/Baiqi/Lua/BaiqiPolicy.lua', 'mod/Baiqi/Lua/BaiqiPlanner.lua'):
            self.lua.execute((ROOT / name).read_text(encoding='utf-8'))
        source = (ROOT / 'mod/Baiqi/Lua/BaiqiController.lua').read_text(encoding='utf-8')
        self.sites = self.lua.execute(source + '\nreturn function(...) local result=SettlementSites(...);return result end\n')
        self.w = self.lua.globals().TestWorld
        self.c = self.lua.globals().BaiqiController
        self.c.RunNow(False)

    def test_failed_high_rank_is_excluded_before_validation(self):
        excluded = self.lua.table()
        excluded[46] = True
        sites = self.sites(self.w.objects.player, self.lua.table(), True, excluded, 2)
        self.assertEqual([s.index for s in sites.values()], [47])

    def test_real_module_reservation_is_respected_for_second_settler(self):
        self.w.withBuilder, self.w.withSettler = False, True
        self.c.RunNow()
        self.assertEqual(self.w.pathQueries[1].target, 46)
        sites = self.sites(self.w.objects.player, self.lua.table(), True, self.lua.table(), 4)
        self.assertEqual([s.index for s in sites.values()], [47])

    def test_hidden_first_hint_still_falls_back_to_next_valid_hint(self):
        self.w.hidden[46] = True
        sites = self.sites(self.w.objects.player, self.lua.table(), True)
        self.assertEqual([s.index for s in sites.values()], [47])

    def test_all_valid_hints_are_checked_without_enumerating_foreign_rosters(self):
        self.lua.execute('''
            TestWorld.settlementRecommendations={46,47,48}
            PlayerManager.GetAliveIDs=function()
                error('Settlement planning must not enumerate foreign city rosters')
            end
        ''')
        sites = self.sites(self.w.objects.player, self.lua.table(), False)
        self.assertEqual({s.index for s in sites.values()}, {46, 47, 48})


if __name__ == '__main__':
    unittest.main()
