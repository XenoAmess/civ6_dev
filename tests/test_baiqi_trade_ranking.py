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

    def food_ranking_fixture(self):
        self.lua.execute('''
            local w=TestWorld;local city=w.objects.city
            w.foodStock=1.74609375;w.foodSurplus=-3;w.foodReads=0
            w.foodPotential={[67]=3,[68]=3,[69]=2,[70]=1}
            w.foodPath={[67]=0,[68]=0,[69]=0,[70]=0}
            w.foodModifiers={[67]=0,[68]=2,[69]=0,[70]=0}
            city.GetGrowth=function()return {
                GetFood=function()return w.foodStock end,
                GetFoodSurplus=function()return w.foodSurplus end}
            end
            YieldTypes=YieldTypes or {};YieldTypes.FOOD=0
            local original=Game.GetTradeManager
            Game.GetTradeManager=function()
                local t=original()
                local function component(key)
                    return function(self,pid,origin,pid2,dest)
                        assert(self==t and pid==7 and pid2==7 and origin==66)
                        w.foodReads=w.foodReads+1
                        if w.failEstimate==dest then error('native estimate unavailable') end
                        return {[1]=w[key][dest]}
                    end
                end
                t.CalculateOriginYieldsFromPotentialRoute=component('foodPotential')
                t.CalculateOriginYieldsFromPath=component('foodPath')
                t.CalculateOriginYieldsFromModifiers=component('foodModifiers')
                return t
            end
        ''')

    def test_low_buffer_prefers_longer_route_with_more_native_food(self):
        self.food_ranking_fixture()
        self.c.RunNow()
        self.assertEqual(self.destination(), (2, 7))
        self.assertEqual(self.w.foodReads, 12)

    def test_danger_on_high_food_route_still_falls_back_to_safe_route(self):
        self.food_ranking_fixture()
        self.w.tradeHidden[54] = True
        self.c.RunNow()
        self.assertEqual(self.destination(), (5, 3))
        self.assertEqual(self.w.tradeReads[54] or 0, 0)
        self.assertEqual([(q.x, q.y) for q in self.w.tradeQualifications.values()],
                         [(2, 7), (5, 3), (5, 3)])

    def test_unknown_or_nonfinite_food_in_any_alternative_restores_original_order(self):
        for native_value in ('nil', 'math.huge', '0/0', '"0"'):
            with self.subTest(native_value=native_value):
                self.setUp()
                self.food_ranking_fixture()
                self.lua.execute('TestWorld.foodModifiers[70]=' + native_value)
                self.c.RunNow()
                self.assertEqual(self.destination(), (5, 3))

    def test_throwing_food_read_keeps_shortest_and_equal_food_uses_original_ties(self):
        for mutation in ('TestWorld.failEstimate=70', 'TestWorld.foodModifiers[68]=0'):
            with self.subTest(mutation=mutation):
                self.setUp()
                self.food_ranking_fixture()
                self.lua.execute(mutation)
                self.c.RunNow()
                self.assertEqual(self.destination(), (5, 3))

    def test_safe_stock_positive_surplus_and_unavailable_stock_do_not_estimate_food(self):
        for state in ('TestWorld.foodStock=2', 'TestWorld.foodSurplus=0.5',
                      'TestWorld.foodStock=nil', 'TestWorld.foodStock=-1'):
            with self.subTest(state=state):
                self.setUp()
                self.food_ranking_fixture()
                self.lua.execute(state)
                self.c.RunNow()
                self.assertEqual(self.destination(), (5, 3))
                self.assertEqual(self.w.foodReads, 0)

    def test_capacity_still_blocks_before_any_food_or_path_reads(self):
        self.food_ranking_fixture()
        self.w.tradeCapacity = 0
        self.c.RunNow()
        self.assertEqual(self.routes(), [])
        self.assertEqual(self.w.foodReads, 0)
        self.assertEqual(len(self.w.tradePathQueries), 0)

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

    def test_late_visibility_in_fresh_command_route_blocks_write(self):
        self.lua.execute('''
            TestWorld.latePathMutationCount=0
            local chosen=0
            TestWorld.tradeOnQualify=function(q)
                if q.x==5 and q.y==3 then
                    chosen=chosen+1
                    if chosen==2 then
                        TestWorld.tradeOnPath=function(dest)
                            if dest==67 then
                                TestWorld.tradeHidden[43]=true
                                TestWorld.latePathMutationCount=TestWorld.latePathMutationCount+1
                            end
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
                    if chosen==2 then return false end
                end
                return true
            end
        ''')
        self.c.RunNow()
        self.assertEqual(self.routes(), [])
        self.assertTrue(all(q.x == 5 and q.y == 3 for q in self.w.tradeQualifications.values()))


if __name__ == '__main__':
    unittest.main()
