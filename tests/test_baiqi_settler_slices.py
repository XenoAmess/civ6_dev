"""Keep settlement priorities and lifecycle while bounding failed path search."""
import unittest
import test_baiqi_path_ranking as path_ranking


class SettlerSliceTests(unittest.TestCase):
    setUp_world = path_ranking.PathRankingTests.setUp
    paths = path_ranking.PathRankingTests.paths
    packet = path_ranking.PathRankingTests.packet

    def setUp(self):
        self.setUp_world()
        self.w.withBuilder, self.w.withSettler = False, True

    def first_failure(self):
        self.lua.execute('TestWorld.paths[46]=false')
        self.c.RunNow()
        self.assertEqual(self.paths(), [(2, 46)])
        self.assertEqual(len(self.w.unitRequests), 0)

    def test_second_rank_remains_available_next_callback(self):
        self.first_failure()
        self.c.RunNow()
        self.assertEqual(self.paths(), [(2, 46), (2, 47)])
        self.assertEqual(self.packet(), (2, 10, 2, 4))

    def test_all_unreachable_only_wait_after_three_callbacks(self):
        self.lua.execute('''
            TestWorld.settlementRecommendations={46,47,48}
            TestWorld.paths[46]=false;TestWorld.paths[47]=false;TestWorld.paths[48]=false
        ''')
        for n in (1, 2, 3):
            before = len(self.w.pathQueries)
            self.c.RunNow()
            self.assertEqual(len(self.w.pathQueries) - before, 1)
            self.assertEqual(len(self.w.unitRequests), int(n == 3))
        self.assertEqual(self.w.unitRequests[1].op, 17)

    def test_new_turn_restarts_higher_rank(self):
        self.first_failure()
        self.w.turn = 2
        self.c.RunNow()
        self.assertEqual(self.paths(), [(2, 46), (2, 46)])
        self.assertEqual(len(self.w.unitRequests), 0)

    def test_position_change_restarts_search(self):
        self.first_failure()
        self.w.settlerPlot = 43
        self.c.RunNow()
        self.assertEqual(self.paths(), [(2, 46), (2, 46)])

    def test_escort_interrupt_invalidates_without_background_order(self):
        self.first_failure()
        self.w.formation = 2
        self.c.RunNow()
        self.assertEqual(self.paths(), [(2, 46)])
        self.assertEqual(len(self.w.unitRequests), 0)
        self.w.formation = 1
        self.lua.execute('TestWorld.paths[46]={42,43,60,61,62,48,46}')
        self.c.RunNow()
        self.assertEqual(self.paths(), [(2, 46), (2, 46)])
        self.assertEqual(self.packet(), (2, 10, 3, 3))

    def test_missing_unit_discards_search(self):
        self.first_failure()
        self.w.withSettler = False
        self.c.RunNow()
        self.w.withSettler = True
        self.lua.execute('TestWorld.paths[46]={42,43,60,61,62,48,46}')
        self.c.RunNow()
        self.assertEqual(self.paths(), [(2, 46), (2, 46)])

    def test_changed_full_id_does_not_keep_slot_search(self):
        self.first_failure()
        self.lua.execute('TestWorld.objects.settler.GetID=function() return 33 end;TestWorld.paths[46]={42,43,60,61,62,48,46}')
        self.c.RunNow()
        self.assertEqual(self.paths(), [(2, 46), (33, 46)])
        self.assertEqual(self.packet(), (33, 10, 3, 3))

    def test_new_foreign_recommendation_is_filtered_on_resume(self):
        self.lua.execute('TestWorld.settlementRecommendations={46,47,48};TestWorld.paths[46]=false')
        self.c.RunNow()
        self.assertEqual(self.paths(), [(2, 46)])
        self.w.siteOwners[47] = 8
        self.c.RunNow()
        self.assertEqual(self.paths(), [(2, 46), (2, 48)])
        self.assertEqual(self.packet(), (2, 10, 3, 3))

    def test_failed_target_is_not_prematurely_reserved_for_other_settler(self):
        self.w.secondSettler = True
        self.lua.execute('TestWorld.settlementRecommendations={46,47,48};TestWorld.paths[46]=false')
        self.c.RunNow()
        self.assertEqual(self.paths(), [(2, 46)])
        self.c.RunNow()
        self.assertEqual(self.paths(), [(2, 46), (2, 47)])
        self.c.RunNow()
        self.assertEqual(self.paths(), [(2, 46), (2, 47), (4, 46)])
        self.c.RunNow()
        self.assertEqual(self.paths(), [(2, 46), (2, 47), (4, 46), (4, 48)])
        self.assertEqual(self.w.unitRequests[2].unit, 4)

    def test_starting_capital_does_not_path_to_distant_hints_before_founding(self):
        self.w.withCity = False
        self.c.RunNow()
        self.assertEqual((self.w.unitRequests[1].unit, self.w.unitRequests[1].op), (2, 11))
        self.assertEqual(self.paths(), [])


if __name__ == '__main__':
    unittest.main()
