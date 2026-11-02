"""Verify selected actions as well as native path-query order in the real controller."""
from pathlib import Path
import unittest
from lupa.lua53 import LuaRuntime

ROOT = Path(__file__).resolve().parents[1]


class PathRankingTests(unittest.TestCase):
    def setUp(self):
        self.lua = LuaRuntime(unpack_returned_tuples=True)
        for name in ('tests/lua/mock_world.lua', 'tests/lua/mock_movement.lua',
                     'tests/lua/mock_path_ranking.lua', 'mod/Baiqi/Lua/BaiqiConfig.lua',
                     'mod/Baiqi/Lua/BaiqiPolicy.lua', 'mod/Baiqi/Lua/BaiqiPlanner.lua',
                     'mod/Baiqi/Lua/BaiqiController.lua'):
            self.lua.execute((ROOT / name).read_text(encoding='utf-8'))
        self.w, self.c = self.lua.globals().TestWorld, self.lua.globals().BaiqiController

    def paths(self):
        return [(q.unit, q.target) for q in self.w.pathQueries.values()]

    def packet(self):
        r = self.w.unitRequests[1]
        return r.unit, r.op, r.params[14], r.params[15]

    def settler(self):
        self.w.withBuilder, self.w.withSettler = False, True

    def test_builder_duplicate_city_hints_need_only_one_path(self):
        self.w.cityCopies = 9
        self.lua.execute('TestWorld.builderRecommendations={43,43}')
        self.c.RunNow()
        self.assertEqual(self.packet(), (3, 10, 3, 3))
        self.assertEqual(self.paths(), [(3, 43)])

    def test_builder_farther_first_and_equal_distance_tie_keep_original_choice(self):
        self.lua.execute('TestWorld.builderRecommendations={45,44,43}')
        self.c.RunNow()
        self.assertEqual(self.packet(), (3, 10, 3, 3))
        self.assertEqual(self.paths(), [(3, 43)])

    def test_builder_unreachable_nearest_checks_next_in_rank_order(self):
        self.lua.execute('TestWorld.builderRecommendations={45,44,43};TestWorld.paths[43]=false')
        self.c.RunNow()
        self.assertEqual(self.paths(), [(3, 43)])
        self.assertEqual(len(self.w.unitRequests), 0)
        self.c.RunNow()
        self.assertEqual(self.packet(), (3, 10, 2, 4))
        self.assertEqual(self.paths(), [(3, 43), (3, 44)])

    def test_builder_unrevealed_recommendation_never_gets_a_path(self):
        self.lua.execute('TestWorld.builderRecommendations={43,44};TestWorld.hidden[43]=true')
        self.c.RunNow()
        self.assertEqual(self.packet(), (3, 10, 2, 4))
        self.assertEqual(self.paths(), [(3, 44)])

    def test_builder_visible_enemy_causes_wait_without_native_path_or_move(self):
        self.lua.execute('TestWorld.builderRecommendations={43,44};TestWorld.enemyPlot=43')
        self.c.RunNow()
        self.assertEqual(self.paths(), [])
        self.assertEqual(len(self.w.unitRequests), 0)
        self.c.RunNow()
        self.assertEqual(self.paths(), [])
        self.assertEqual((self.w.unitRequests[1].unit, self.w.unitRequests[1].op), (3, 17))

    def test_builder_first_reachable_write_rejection_does_not_try_other_destination(self):
        self.lua.execute('TestWorld.builderRecommendations={43,44};TestWorld.rejectMoveX=3')
        self.c.RunNow()
        self.assertEqual(self.paths(), [(3, 43)])
        self.assertEqual(len(self.w.unitRequests), 1)
        self.assertEqual(self.w.unitRequests[1].op, 17)

    def test_settler_uses_native_rank_instead_of_nearest_distance_and_stops_early(self):
        self.settler()
        self.lua.execute('TestWorld.settlementRecommendations={46,48,47}')
        self.c.RunNow()
        self.assertEqual(self.packet(), (2, 10, 3, 3))
        self.assertEqual(self.paths(), [(2, 46)])

    def test_settler_unreachable_best_falls_back_without_changing_score_order(self):
        self.settler()
        self.lua.execute('TestWorld.paths[46]=false;TestWorld.settlementRecommendations={46,47,48}')
        self.c.RunNow()
        self.assertEqual(self.packet(), (2, 10, 2, 4))
        self.assertEqual(self.paths(), [(2, 46), (2, 47)])

    def test_settler_reservation_skips_path_for_other_settlers_target(self):
        self.settler()
        self.w.secondSettler = True
        self.c.RunNow()
        self.c.RunNow()
        self.assertEqual(self.paths(), [(2, 46), (4, 47)])
        self.assertEqual(len(self.w.unitRequests), 2)
        self.assertEqual(self.w.unitRequests[2].unit, 4)
        self.assertEqual((self.w.unitRequests[2].params[14], self.w.unitRequests[2].params[15]), (2, 4))

    def test_settler_already_at_selected_site_founds_without_querying_paths(self):
        self.settler()
        self.w.settlerPlot = 46
        self.c.RunNow()
        self.assertEqual((self.w.unitRequests[1].unit, self.w.unitRequests[1].op), (2, 11))
        self.assertEqual(self.paths(), [])

    def test_starting_capital_without_hints_still_founds_without_paths(self):
        self.settler()
        self.w.withCity = False
        self.lua.execute('TestWorld.settlementRecommendations={}')
        self.c.RunNow()
        self.assertEqual((self.w.unitRequests[1].unit, self.w.unitRequests[1].op), (2, 11))
        self.assertEqual(self.paths(), [])

    def test_settler_escort_retains_zero_background_paths_and_orders(self):
        self.settler()
        self.w.formation = 2
        self.c.RunNow()
        self.assertEqual(self.paths(), [])
        self.assertEqual(len(self.w.unitRequests), 0)


if __name__ == '__main__':
    unittest.main()
