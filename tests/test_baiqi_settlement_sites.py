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

    def test_selected_site_remains_first_after_native_hint_disappears(self):
        self.lua.execute('TestWorld.settlementRecommendations={47}')
        sites = self.sites(self.w.objects.player, self.lua.table(), True,
                           self.lua.table(), 2, 46)
        self.assertEqual([s.index for s in sites.values()], [46])

    def test_selected_site_is_deduplicated_against_native_hints(self):
        self.lua.execute('TestWorld.settlementRecommendations={47,46,46}')
        sites = self.sites(self.w.objects.player, self.lua.table(), False,
                           self.lua.table(), 2, 46)
        self.assertEqual([s.index for s in sites.values()], [46, 47])

    def test_selected_site_cannot_bypass_search_exclusion(self):
        excluded = self.lua.table_from({46: True})
        sites = self.sites(self.w.objects.player, self.lua.table(), True,
                           excluded, 2, 46)
        self.assertEqual([s.index for s in sites.values()], [47])

    def test_selected_site_cannot_bypass_another_settlers_reservation(self):
        self.w.withBuilder, self.w.withSettler = False, True
        self.c.RunNow()
        sites = self.sites(self.w.objects.player, self.lua.table(), True,
                           self.lua.table(), 4, 46)
        self.assertEqual([s.index for s in sites.values()], [47])

    def test_selected_site_rechecks_current_geometry_and_ownership(self):
        changes = (
            'TestWorld.hidden[46]=true',
            'TestWorld.siteOwners[46]=8',
            'Map.GetPlotByIndex(46).GetFeatureType=function()return 2 end',
            'Map.GetPlotByIndex(46).IsWater=function()return true end',
            'Map.GetPlotByIndex(46).IsImpassable=function()return true end',
            'Map.GetPlotByIndex(46).IsCity=function()return true end',
        )
        for change in changes:
            with self.subTest(change=change):
                self.setUp()
                self.lua.execute(change)
                sites = self.sites(self.w.objects.player, self.lua.table(), True,
                                   self.lua.table(), 2, 46)
                self.assertNotIn(46, [s.index for s in sites.values()])

    def test_selected_site_rechecks_visible_threats(self):
        self.w.enemyPlot = 46
        sites = self.sites(self.w.objects.player, self.lua.table(), False,
                           self.lua.table(), 2, 46)
        self.assertNotIn(46, [s.index for s in sites.values()])

    def test_selected_site_rechecks_distance_to_current_owned_city(self):
        self.lua.execute('''
            TestWorld.objects.city.GetX=function()return 8 end
            TestWorld.objects.city.GetY=function()return 2 end
        ''')
        sites = self.sites(self.w.objects.player, self.lua.table(), False,
                           self.lua.table(), 2, 46)
        self.assertEqual(len(sites), 0)


if __name__ == '__main__':
    unittest.main()
