"""Select legal next production over a proved single completed native head."""
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

    def test_legal_next_production_uses_native_replace_packet_and_waits_for_matching_ack(self):
        self.c.RunNow()
        packet = self.w.cityRequests[1]
        self.assertEqual((packet.city,packet.op,packet.params[6],packet.params[889],packet.params[3]), (66,1,888,0,707))
        self.c.Update(0.35)
        self.assertFalse(any('queue_observed' in s for s in self.logs))
        self.w.AcceptReplacement();self.c.RunNow()
        self.assertEqual(len(self.w.cityRequests), 1)
        self.assertEqual(self.w.granaryProgress, 54)
        self.assertTrue(any('queue_observed' in s for s in self.logs))

    def test_future_valid_item_is_kept_without_replacing_any_queue_entry(self):
        self.lua.execute('TestWorld.queues[66][2]={ProjectType="PROJECT_TEST",Directive=5}')
        self.c.RunNow()
        self.assertEqual(len(self.w.cityRequests), 0)
        self.assertEqual(len(self.w.queues[66]), 2)
        self.assertEqual(self.w.queues[66][2].ProjectType, 'PROJECT_TEST')

    def test_active_incomplete_pillaged_missing_asset_unknown_cost_unit_and_project_heads_are_untouched(self):
        for code in (
            'TestWorld.ghost=false', 'TestWorld.granaryProgress=24', 'TestWorld.granaryPillaged=true',
            'TestWorld.granaryExists=false', 'TestWorld.granaryCost=nil',
            'TestWorld.queues[66]={{UnitType=0}}', 'TestWorld.queues[66]={{ProjectType="PROJECT_TEST"}}',
        ):
            with self.subTest(code=code):
                self.setUp();self.lua.execute(code);self.c.RunNow()
                self.assertEqual(len(self.w.cityRequests), 0, self.logs)

    def test_unknown_replacement_survives_delay_and_turn_change_without_overwriting_alternate_work(self):
        self.c.RunNow();self.c.Update(2)
        self.w.turn += 1
        self.c.Update(3600)
        self.assertEqual(len(self.w.cityRequests), 1)
        self.assertFalse(any('queue_observed' in s for s in self.logs))
        self.assertEqual(sum('queue_replacement_unresolved' in s for s in self.logs), 1)
        self.w.AcceptReplacement();self.c.RunNow()
        self.assertEqual(sum('queue_observed' in s for s in self.logs), 1)

    def test_busy_pending_replacement_is_not_repeated(self):
        self.c.RunNow()
        self.w.busy=True;self.w.turn+=1
        self.c.Update(10)
        self.assertEqual(len(self.w.cityRequests), 1)
        self.w.AcceptReplacement();self.w.busy=False
        self.c.RunNow()
        self.assertTrue(any('queue_observed' in s for s in self.logs))
        self.assertEqual(len(self.w.cityRequests), 1)

    def test_owner_head_or_future_queue_changes_during_final_gate_prevent_stale_replacement(self):
        for change in (
            'TestWorld.objects.city.GetOwner=function() return 8 end',
            'TestWorld.queues[66]={{UnitType=0}}', 'TestWorld.granaryPillaged=true',
            'TestWorld.queues[66][2]={ProjectType="PROJECT_TEST"}',
        ):
            with self.subTest(change=change):
                self.setUp()
                self.lua.execute('TestWorld.onReplacementGate=function(n) if n==2 then '+change+' end end')
                self.c.RunNow()
                self.assertEqual(len(self.w.cityRequests), 0, self.logs)

    def test_absent_old_head_or_unrelated_work_does_not_confirm_selected_production(self):
        for queue in ('{}', '{{ProjectType="PROJECT_TEST"}}'):
            with self.subTest(queue=queue):
                self.setUp();self.c.RunNow()
                self.lua.execute('TestWorld.queues[66]='+queue+';TestWorld.ghost=false')
                self.w.turn+=1;self.c.Update(10)
                self.assertFalse(any('queue_observed' in s for s in self.logs))
                self.assertEqual(len(self.w.cityRequests), 1)

    def test_completed_district_can_receive_new_work_but_pillaged_head_cannot(self):
        self.lua.execute('TestWorld.queues[66]={{DistrictType=7}};TestWorld.campusPillaged=false;TestWorld.campusProgress=72;TestWorld.allowTrader=true')
        self.c.RunNow()
        self.assertEqual(self.w.cityRequests[1].params[6], 888)
        self.assertEqual(self.w.cityRequests[1].params[4], 203)
        self.setUp()
        self.lua.execute('TestWorld.queues[66]={{DistrictType=7}};TestWorld.campusProgress=72')
        self.c.RunNow()
        self.assertEqual(len(self.w.cityRequests), 0)

    def test_pending_trader_replacement_reserves_capacity_while_old_completed_head_remains(self):
        self.w.allowTrader=True;self.w.campusPillaged=False
        self.c.RunNow();self.c.RunNow()
        self.assertEqual(len(self.w.cityRequests), 1)
        self.assertEqual(self.w.cityRequests[1].params[4], 203)

    def test_native_acknowledged_replacement_is_counted_once_for_next_city_capacity(self):
        self.w.allowTrader=True;self.w.tradeCapacity=2;self.w.campusPillaged=False
        self.c.RunNow()
        self.assertEqual(self.w.cityRequests[1].params[4], 203)
        self.w.AcceptReplacement();self.c.RunNow()
        self.assertEqual(len(self.w.cityRequests), 2)
        self.assertEqual((self.w.cityRequests[2].city,self.w.cityRequests[2].params[4]), (67,203))

    def test_completed_existing_maintenance_is_not_a_second_commitment(self):
        self.w.allowTrader=True;self.w.tradeCapacity=2;self.w.campusPillaged=False
        self.lua.execute('''
GameInfo.Buildings[0].Maintenance=2;GameInfo.Units.UNIT_TRADER.Maintenance=1
TestWorld.objects.player.GetTreasury=function() return {
 GetGoldBalance=function() return 100 end,GetGoldYield=function() return 5 end,
 GetTotalMaintenance=function() return 2 end} end
''')
        self.c.RunNow();self.c.RunNow()
        self.assertEqual(len(self.w.cityRequests), 1)
        self.assertEqual(self.w.cityRequests[1].params[4], 203)

    def test_native_rejected_new_item_never_sends_a_replacement(self):
        self.w.rejectReplacement=True
        self.c.RunNow()
        self.assertEqual(len(self.w.cityRequests), 0)


if __name__ == '__main__':
    unittest.main()
