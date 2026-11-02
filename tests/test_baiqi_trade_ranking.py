"""Preserve safe domestic alternatives while avoiding losing-route safety reads."""
from pathlib import Path
import unittest
from lupa.lua53 import LuaRuntime

ROOT = Path(__file__).resolve().parents[1]


class TradeRankingTests(unittest.TestCase):
    def setUp(self):
        self.lua = LuaRuntime(unpack_returned_tuples=True)
        for name in ('tests/lua/mock_world.lua', 'tests/lua/mock_trade.lua',
                     'tests/lua/mock_trade_ranking.lua', 'mod/Baiqi/Lua/BaiqiConfig.lua',
                     'mod/Baiqi/Lua/BaiqiPolicy.lua', 'mod/Baiqi/Lua/BaiqiPlanner.lua',
                     'mod/Baiqi/Lua/BaiqiController.lua'):
            self.lua.execute((ROOT / name).read_text(encoding='utf-8'))
        self.w = self.lua.globals().TestWorld
        self.c = self.lua.globals().BaiqiController

    def routes(self):
        return [r for r in self.w.unitRequests.values() if r.op == 18]

    def destination(self):
        routes = self.routes()
        self.assertEqual(len(routes), 1)
        return routes[0].params.x0, routes[0].params.y0

    def test_shortest_safe_path_uses_city_id_tie_in_unsorted_iteration(self):
        self.c.RunNow()
        self.assertEqual(self.destination(), (5, 3))

    def test_losing_long_route_does_not_query_its_remote_visible_units(self):
        self.c.RunNow()
        self.assertEqual(self.destination(), (5, 3))
        self.assertEqual(self.w.tradeReads[48] or 0, 0)
        self.assertTrue(all(q.x == 5 and q.y == 3 for q in self.w.tradeQualifications.values()))

    def test_route_neighborhoods_are_reused_only_within_each_fresh_validation(self):
        self.c.RunNow()
        self.assertEqual(self.destination(), (5, 3))
        self.assertLessEqual(max(self.w.tradeReads.values()), 3)

    def test_unsafe_shorter_route_falls_back_to_safe_longer_domestic_route(self):
        self.lua.execute('TestWorld.tradeCityOrder={67,68,66};TestWorld.tradeEnemy=45')
        self.c.RunNow()
        self.assertEqual(self.destination(), (2, 7))

    def test_new_foreign_path_falls_back_without_crossing_border(self):
        self.lua.execute('TestWorld.tradeCityOrder={67,68,66};TestWorld.tradeOwners[45]=8')
        self.c.RunNow()
        self.assertEqual(self.destination(), (2, 7))

    def test_hidden_shorter_path_falls_back_without_hidden_unit_reads(self):
        self.lua.execute('TestWorld.tradeCityOrder={67,68,66};TestWorld.tradeHidden[45]=true')
        self.c.RunNow()
        self.assertEqual(self.destination(), (2, 7))
        self.assertEqual(self.w.tradeReads[45] or 0, 0)

    def test_capacity_zero_has_no_path_queries_or_route_submission(self):
        self.w.tradeCapacity = 0
        self.c.RunNow()
        self.assertEqual(self.routes(), [])
        self.assertEqual(len(self.w.tradePathQueries), 0)

    def test_late_enemy_in_fresh_command_route_blocks_write(self):
        self.lua.execute('''
            TestWorld.latePathMutationCount=0
            TestWorld.tradeOnQualify=function(q)
                if q.x==5 and q.y==3 then
                    TestWorld.tradeOnPath=function(dest)
                        if dest==67 then
                            TestWorld.tradeEnemy=45
                            TestWorld.latePathMutationCount=TestWorld.latePathMutationCount+1
                        end
                    end
                end
                return true
            end
        ''')
        self.c.RunNow()
        self.assertEqual(self.w.latePathMutationCount, 1)
        self.assertEqual(self.routes(), [])
        self.assertEqual([r.op for r in self.w.unitRequests.values()], [17])

    def test_final_write_qualification_rejection_does_not_select_another_route(self):
        self.lua.execute('''
            local chosen=0
            TestWorld.tradeOnQualify=function(q)
                if q.x==5 and q.y==3 then
                    chosen=chosen+1
                    if chosen==3 then return false end
                end
                return true
            end
        ''')
        self.c.RunNow()
        self.assertEqual(self.routes(), [])
        self.assertTrue(all(q.x == 5 and q.y == 3 for q in self.w.tradeQualifications.values()))


if __name__ == '__main__':
    unittest.main()
