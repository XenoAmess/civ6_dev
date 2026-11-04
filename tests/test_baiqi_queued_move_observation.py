import unittest
import test_baiqi_controller as base


class QueuedMoveObservationTests(unittest.TestCase):
    def setUp(self):
        base.BaiqiControllerTests.setUp(self)
        base.BaiqiControllerTests.movement(self)
        self.w,self.c=self.world,self.controller
        self.lua.execute('TestWorld.logs={};print=function(s) table.insert(TestWorld.logs,s) end')

    def observed(self):
        return [line for line in self.w.logs.values() if 'BAIQI|observed|' in line]

    def test_turn_refresh_preserves_queued_move_until_coordinate_arrival(self):
        self.w.builderMoves=1
        self.c.RunNow()
        self.w.queuedDestination=43
        self.w.turn+=1
        self.w.builderMoves=2
        self.c.Update(.35)
        self.assertEqual(self.observed(),[])
        self.assertEqual([(r.unit,r.op) for r in self.w.unitRequests.values()],[(3,10)])
        self.w.builderPlot=43
        self.w.queuedDestination=None
        self.c.Update(.35)
        self.assertEqual([(r.unit,r.op) for r in self.w.unitRequests.values()],[(3,10),(3,12)])
        self.assertEqual(len(self.observed()),1)

    def test_same_turn_move_cost_change_does_not_complete_queued_route(self):
        self.c.RunNow()
        self.w.queuedDestination=43
        self.w.builderMoves=1
        self.c.RunNow(False)
        self.assertEqual(self.observed(),[])
        self.assertEqual([(r.unit,r.op) for r in self.w.unitRequests.values()],[(3,10)])

    def test_unknown_coordinates_and_changed_moves_do_not_complete_move(self):
        self.c.RunNow()
        self.w.queuedDestination=43
        self.w.builderMoves=1
        self.lua.execute('TestWorld.objects.builder.GetX=function() return nil end')
        self.c.RunNow(False)
        self.assertEqual(self.observed(),[])
        self.assertEqual([(r.unit,r.op) for r in self.w.unitRequests.values()],[(3,10)])

    def test_non_move_build_still_observes_consumed_movement(self):
        self.w.builderPlot=43
        self.c.RunNow()
        self.assertEqual([(r.unit,r.op) for r in self.w.unitRequests.values()],[(3,12)])
        self.w.builderMoves=1
        self.c.RunNow(False)
        self.assertEqual(len(self.observed()),1)
        self.assertIn('kind=BUILD_IMPROVEMENT',self.observed()[0])
        self.assertEqual([(r.unit,r.op) for r in self.w.unitRequests.values()],[(3,12)])
