"""Remove a proved completed idle head without discarding valid queued work."""
from pathlib import Path
import unittest
from lupa.lua53 import LuaRuntime

ROOT = Path(__file__).resolve().parents[1]


class BaiqiCompletedQueueTests(unittest.TestCase):
    def setUp(self):
        self.lua = LuaRuntime(unpack_returned_tuples=True)
        for p in ('tests/lua/mock_world.lua', 'tests/lua/mock_trade.lua', 'tests/lua/mock_completed_queue.lua',
                  'mod/Baiqi/Lua/BaiqiConfig.lua', 'mod/Baiqi/Lua/BaiqiPolicy.lua',
                  'mod/Baiqi/Lua/BaiqiPlanner.lua', 'mod/Baiqi/Lua/BaiqiController.lua'):
            self.lua.execute((ROOT/p).read_text(encoding='utf-8'))
        self.w = self.lua.globals().TestWorld
        self.c = self.lua.globals().BaiqiController
        self.logs = []
        self.lua.globals().print = lambda *args: self.logs.append(' '.join(map(str,args)))

    def test_delayed_remove_waits_for_real_head_absence_then_queues_campus_same_turn(self):
        self.c.RunNow()
        packet = self.w.cityRequests[1]
        self.assertEqual((packet.city,packet.op,packet.params[6],packet.params[778]), (66,1,777,0))
        self.c.Update(0.35)
        self.assertEqual(len(self.w.cityRequests), 1)
        self.assertFalse(any('queue_cleanup_observed' in s for s in self.logs))
        self.w.AcceptCleanup()
        self.c.RunNow()
        self.assertEqual(len(self.w.cityRequests), 2)
        self.assertEqual(self.w.cityRequests[2].params[3], 707)
        self.assertEqual(self.w.granaryProgress, 54)
        self.assertTrue(any('queue_cleanup_observed' in s for s in self.logs))

    def test_future_valid_item_is_preserved_and_does_not_receive_new_production(self):
        self.lua.execute('TestWorld.queues[66][2]={ProjectType="PROJECT_TEST",Directive=5}')
        self.c.RunNow()
        self.w.AcceptCleanup()
        self.c.RunNow()
        self.assertEqual(len(self.w.cityRequests), 1)
        self.assertEqual(len(self.w.queues[66]), 1)
        self.assertEqual(self.w.queues[66][1].ProjectType, 'PROJECT_TEST')

    def test_active_incomplete_pillaged_missing_asset_unknown_cost_and_unit_head_are_untouched(self):
        for code in (
            'TestWorld.ghost=false', 'TestWorld.granaryProgress=24', 'TestWorld.granaryPillaged=true',
            'TestWorld.granaryExists=false', 'TestWorld.granaryCost=nil',
            'TestWorld.queues[66]={{UnitType=0}}', 'TestWorld.queues[66]={{ProjectType="PROJECT_TEST"}}',
        ):
            with self.subTest(code=code):
                self.setUp();self.lua.execute(code);self.c.RunNow()
                self.assertEqual(len(self.w.cityRequests), 0, self.logs)

    def test_rejected_or_unobserved_cleanup_does_not_repeat_or_fake_ack(self):
        self.c.RunNow()
        self.c.Update(2)
        self.c.Update(10)
        self.assertEqual(len(self.w.cityRequests), 1)
        self.assertFalse(any('queue_cleanup_observed' in s for s in self.logs))
        self.assertEqual(sum('reason=native_idle_unchanged_head' in s for s in self.logs), 1)
        self.w.turn += 1
        self.c.RunNow()
        self.assertEqual(len(self.w.cityRequests), 2)
        self.setUp();self.w.rejectCleanup=True;self.c.RunNow()
        self.assertEqual(len(self.w.cityRequests), 0)

    def test_busy_pending_cleanup_survives_turn_change_without_duplicate_remove(self):
        self.c.RunNow()
        self.w.busy=True;self.w.turn+=1
        self.c.Update(10)
        self.assertEqual(len(self.w.cityRequests), 1)
        self.w.AcceptCleanup();self.w.busy=False
        self.c.RunNow()
        self.assertEqual(len(self.w.cityRequests), 2)
        self.assertEqual(self.w.cityRequests[2].params[3], 707)

    def test_owner_or_head_changes_during_final_gate_prevent_stale_remove(self):
        for code in (
            'TestWorld.onCleanupGate=function() TestWorld.objects.city.GetOwner=function() return 8 end end',
            'TestWorld.onCleanupGate=function() TestWorld.queues[66]={{UnitType=0}} end',
            'TestWorld.onCleanupGate=function() TestWorld.granaryPillaged=true end',
        ):
            with self.subTest(code=code):
                self.setUp();self.lua.execute(code);self.c.RunNow()
                self.assertEqual(len(self.w.cityRequests), 0, self.logs)

    def test_tail_removal_with_same_head_is_not_acknowledgement(self):
        self.lua.execute('TestWorld.queues[66][2]={ProjectType="PROJECT_TEST",Directive=5}')
        self.c.RunNow()
        self.lua.execute('table.remove(TestWorld.queues[66],2)')
        self.c.Update(0.35)
        self.assertFalse(any('queue_cleanup_observed' in s for s in self.logs))
        self.assertEqual(len(self.w.cityRequests), 1)

    def test_completed_district_head_can_be_cleaned_but_pillaged_one_cannot(self):
        self.lua.execute('TestWorld.queues[66]={{DistrictType=7}};TestWorld.campusPillaged=false;TestWorld.campusProgress=72')
        self.c.RunNow()
        self.assertEqual(len(self.w.cityRequests), 1)
        self.assertEqual(self.w.cityRequests[1].params[6], 777)
        self.setUp()
        self.lua.execute('TestWorld.queues[66]={{DistrictType=7}};TestWorld.campusProgress=72')
        self.c.RunNow()
        self.assertEqual(len(self.w.cityRequests), 0)


if __name__ == '__main__':
    unittest.main()
