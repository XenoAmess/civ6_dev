"""Bound real builder planning work without losing unfinished choices."""
import unittest
import test_baiqi_path_ranking as path_ranking


class BuilderSliceTests(unittest.TestCase):
    setUp = path_ranking.PathRankingTests.setUp
    paths = path_ranking.PathRankingTests.paths
    packet = path_ranking.PathRankingTests.packet

    def first_failure(self):
        self.lua.execute('TestWorld.builderRecommendations={43,44};TestWorld.paths[43]=false')
        self.c.RunNow()
        self.assertEqual(self.paths(), [(3, 43)])
        self.assertEqual(len(self.w.unitRequests), 0)

    def test_one_path_per_callback_and_reachable_second_choice(self):
        self.first_failure()
        self.c.RunNow()
        self.assertEqual(self.paths(), [(3, 43), (3, 44)])
        self.assertEqual(self.packet(), (3, 10, 2, 4))

    def test_three_failed_candidates_only_wait_after_exhaustion(self):
        self.lua.execute('''
            TestWorld.builderRecommendations={43,44,45}
            TestWorld.paths[43]=false;TestWorld.paths[44]=false;TestWorld.paths[45]=false
        ''')
        for count in (1, 2, 3):
            before = len(self.w.pathQueries)
            self.c.RunNow()
            self.assertEqual(len(self.w.pathQueries) - before, 1)
            self.assertEqual(len(self.w.unitRequests), int(count == 3))
        self.assertEqual(self.w.unitRequests[1].op, 17)

    def test_new_turn_restarts_current_priorities(self):
        self.first_failure()
        self.w.turn = 2
        self.c.RunNow()
        self.assertEqual(self.paths(), [(3, 43), (3, 43)])
        self.assertEqual(len(self.w.unitRequests), 0)

    def test_changed_moves_restart_failed_target(self):
        self.first_failure()
        self.w.builderMoves = 1
        self.lua.execute('TestWorld.paths[43]={42,43}')
        self.c.RunNow()
        self.assertEqual(self.paths(), [(3, 43), (3, 43)])
        self.assertEqual(self.packet(), (3, 10, 3, 3))

    def test_new_nearer_recommendation_keeps_current_priority(self):
        self.lua.execute('TestWorld.builderRecommendations={44,45};TestWorld.paths[44]=false')
        self.c.RunNow()
        self.assertEqual(self.paths(), [(3, 44)])
        self.assertEqual(len(self.w.unitRequests), 0)
        self.lua.execute('TestWorld.builderRecommendations={45,44,43}')
        self.c.RunNow()
        self.assertEqual(self.paths(), [(3, 44), (3, 43)])
        self.assertEqual(self.packet(), (3, 10, 3, 3))

    def test_escort_interrupt_discards_search_without_moving_army(self):
        self.first_failure()
        self.w.formation = 2
        self.c.RunNow()
        self.assertEqual(self.paths(), [(3, 43)])
        self.assertEqual(len(self.w.unitRequests), 0)
        self.w.formation = 1
        self.lua.execute('TestWorld.paths[43]={42,43}')
        self.c.RunNow()
        self.assertEqual(self.paths(), [(3, 43), (3, 43)])
        self.assertEqual(self.packet(), (3, 10, 3, 3))

    def test_missing_unit_discards_index_only_search(self):
        self.first_failure()
        self.w.withBuilder = False
        self.c.RunNow()
        self.w.withBuilder = True
        self.lua.execute('TestWorld.paths[43]={42,43}')
        self.c.RunNow()
        self.assertEqual(self.paths(), [(3, 43), (3, 43)])

    def test_unit_full_id_change_restarts_without_slot_reuse(self):
        self.first_failure()
        self.lua.execute('TestWorld.objects.builder.GetID=function() return 33 end;TestWorld.paths[43]={42,43}')
        self.c.RunNow()
        self.assertEqual(self.paths(), [(3, 43), (33, 43)])
        self.assertEqual(self.packet(), (33, 10, 3, 3))

    def test_pending_write_stays_single_after_planning_finishes(self):
        self.first_failure()
        self.c.RunNow()
        self.c.RunNow()
        self.assertEqual(self.paths(), [(3, 43), (3, 44)])
        self.assertEqual(len(self.w.unitRequests), 1)


if __name__ == '__main__':
    unittest.main()
