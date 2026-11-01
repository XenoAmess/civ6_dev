"""Exercise production packets and fresh site gates through the real controller."""
from pathlib import Path
import unittest
from lupa.lua53 import LuaRuntime

ROOT = Path(__file__).resolve().parents[1]


class SettlementQueryTests(unittest.TestCase):
    def setUp(self):
        self.lua = LuaRuntime(unpack_returned_tuples=True)
        for name in ('tests/lua/mock_world.lua', 'tests/lua/mock_trade.lua',
                     'mod/Baiqi/Lua/BaiqiConfig.lua', 'mod/Baiqi/Lua/BaiqiPolicy.lua',
                     'mod/Baiqi/Lua/BaiqiPlanner.lua', 'mod/Baiqi/Lua/BaiqiController.lua'):
            self.lua.execute((ROOT / name).read_text(encoding='utf-8'))
        self.w = self.lua.globals().TestWorld
        self.c = self.lua.globals().BaiqiController
        self.w.EnableSettlerSite()
        self.w.productionMode, self.w.withTrader = True, False

    def test_nonsettler_production_never_queries_settlement_recommendations(self):
        for unit_hash, extra_army in ((203, 0), (202, 0), (200, 2)):
            with self.subTest(unit_hash=unit_hash):
                self.setUp()
                self.w.productionHash, self.w.extraArmy = unit_hash, extra_army
                self.c.RunNow()
                self.assertEqual(self.w.settlementQueries or 0, 0)
                self.assertEqual(self.w.cityRequests[1].params[4], unit_hash)
                self.assertEqual(len(self.w.unitRequests), 0)

    def test_actual_settler_dispatch_queries_initial_and_fresh_sites_then_reserves_budget(self):
        self.w.productionHash = 201
        self.c.RunNow()
        self.c.RunNow()
        self.assertEqual(self.w.settlementQueries, 2)
        self.assertEqual(len(self.w.cityRequests), 1)
        self.assertEqual(self.w.cityRequests[1].params[4], 201)

    def test_existing_queued_settler_skips_query_and_uses_legal_fallback(self):
        self.w.productionHash, self.w.allowProject = 201, True
        self.lua.execute('TestWorld.queues[66]={{UnitType=1}}')
        self.c.RunNow()
        self.assertEqual(self.w.settlementQueries or 0, 0)
        self.assertEqual(len(self.w.cityRequests), 1)
        self.assertEqual((self.w.cityRequests[1].city, self.w.cityRequests[1].params[5]), (67, 301))

    def test_no_safe_site_keeps_settlers_out_of_both_real_production_packets(self):
        self.w.productionHash, self.w.allowProject, self.w.noSettlementSite = 201, True, True
        self.c.RunNow()
        self.c.RunNow()
        self.assertEqual(self.w.settlementQueries, 2)
        self.assertEqual(len(self.w.cityRequests), 2)
        self.assertTrue(all(r.params[5] == 301 for r in self.w.cityRequests.values()))

    def test_site_lost_before_dispatch_rejects_settler_and_replans_fallback(self):
        self.w.productionHash, self.w.allowProject, self.w.loseSettlementSite = 201, True, True
        self.w.blockSecondCity = True
        self.c.RunNow()
        self.assertEqual(self.w.settlementQueries, 2)
        self.assertEqual(len(self.w.cityRequests), 0)
        self.c.RunNow()
        self.assertEqual(len(self.w.cityRequests), 1)
        self.assertEqual(self.w.cityRequests[1].params[5], 301)

    def test_production_existence_query_stops_after_first_safe_recommendation(self):
        self.w.productionHash = 201
        self.lua.execute('''
          TestWorld.settlementRecommendations={{SettlingLocation=44},{SettlingLocation=45}}
          TestWorld.unneededSiteReads=0
          local native=Map.GetPlotByIndex
          Map.GetPlotByIndex=function(index)
            if index==45 then TestWorld.unneededSiteReads=TestWorld.unneededSiteReads+1 end
            return native(index)
          end
        ''')
        self.c.RunNow()
        self.assertEqual(self.w.unneededSiteReads, 0)
        self.assertEqual(self.w.cityRequests[1].params[4], 201)


if __name__ == '__main__':
    unittest.main()
