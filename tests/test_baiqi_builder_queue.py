"""Preserve actual builder queues across new proposals and native callbacks."""
from pathlib import Path
import os
import unittest

from lupa.lua51 import LuaRuntime

ROOT = Path(__file__).resolve().parents[1]


class BuilderQueueTests(unittest.TestCase):
    def setUp(self):
        self.lua = LuaRuntime(unpack_returned_tuples=True)
        for name in ('tests/lua/mock_world.lua', 'tests/lua/mock_movement.lua',
                     'tests/lua/mock_path_ranking.lua', 'mod/Baiqi/Lua/BaiqiConfig.lua',
                     'mod/Baiqi/Lua/BaiqiPolicy.lua', 'mod/Baiqi/Lua/BaiqiPlanner.lua'):
            self.lua.execute((ROOT / name).read_text(encoding='utf-8'))
        self.lua.execute('''
local w=TestWorld
w.withBuilder=true;w.withSettler=false;w.queueSize=1
ActivityTypes={ACTIVITY_AWAKE=20,ACTIVITY_HOLD=21}
w.objects.builder.IsReadyToSelect=function()return true end
w.objects.builder.IsReadyToMove=function()return true end
UnitManager.GetActivityType=function()return ActivityTypes.ACTIVITY_AWAKE end
GameInfo.UnitOperations=GameInfo.UnitOperations or {}
GameInfo.UnitOperations.UNITOPERATION_SKIP_TURN={Hash=17}
UnitOperationTypes.BUILD_IMPROVEMENT_ADJACENT=18
GameInfo.Improvements.IMPROVEMENT_SKI_RESORT={Index=50,Hash=505,ImprovementType='IMPROVEMENT_SKI_RESORT'}
for _,id in ipairs({42,43})do Map.GetPlotByIndex(id).GetDistrictType=function()return -1 end end
''')
        source = Path(os.environ.get('BAIQI_BUILDER_QUEUE_CONTROLLER', str(ROOT / 'mod/Baiqi/Lua/BaiqiController.lua')))
        self.private = self.lua.execute(source.read_text(encoding='utf-8')
            + '\nreturn {Request=RequestCivilian,Standby=RequestCivilianStandby,Queue=SettlerQueueIdle,'
            + 'Pending=function()return pendingUnits end}\n')
        self.g = self.lua.globals()
        self.w = self.g.TestWorld
        self.c = self.g.BaiqiController
        self.c.RunNow(False)
        self.ctx = self.lua.table_from(dict(player=7, localPlayer=7, isBaiqi=True,
                                            activeTurn=True, enabled=True))

    def requests(self):
        return [(r.unit, r.op) for r in self.w.unitRequests.values()]

    def write(self, operation='MOVE_TO'):
        plot = 43 if operation in ('MOVE_TO', 'BUILD_IMPROVEMENT_ADJACENT') else 42
        improvement = 505 if operation == 'BUILD_IMPROVEMENT_ADJACENT' else 904
        return self.private.Request(self.ctx, self.lua.table(), self.w.objects.builder,
                                    operation, self.g.Map.GetPlotByIndex(plot), improvement)

    def test_existing_destination_blocks_real_builder_run(self):
        for destination in (0, 2350):
            with self.subTest(destination=destination):
                self.setUp(); self.w.queuedDestination = destination
                self.c.RunNow()
                self.assertEqual(self.requests(), [])
                self.assertEqual(self.w.queuedDestination, destination)
                self.assertIsNone(self.private.Pending()[3])

    def test_existing_queue_blocks_every_builder_operation_at_writer(self):
        for operation in ('MOVE_TO', 'BUILD_IMPROVEMENT', 'BUILD_IMPROVEMENT_ADJACENT', 'REPAIR', 'SKIP_TURN'):
            with self.subTest(operation=operation):
                self.setUp(); self.w.queuedDestination = 2350
                self.assertFalse(self.write(operation)[0])
                self.assertEqual(self.requests(), [])
                self.assertEqual(self.w.queuedDestination, 2350)

    def test_standby_preserves_queue_and_nil_still_allows_hold(self):
        self.w.queuedDestination = 2350
        self.assertFalse(self.private.Standby(self.w.objects.builder))
        self.assertEqual(self.requests(), [])
        self.assertEqual(self.w.queuedDestination, 2350)
        self.setUp()
        self.assertTrue(self.private.Standby(self.w.objects.builder))
        self.assertEqual(self.requests(), [(3, 17)])

    def test_nil_queue_keeps_normal_builder_move(self):
        self.c.RunNow()
        self.assertEqual(self.requests(), [(3, 10)])

    def test_missing_throw_non_nil_and_multireturn_getters_never_authorize(self):
        changes = ('UnitManager.GetQueuedDestination=nil',
                   "UnitManager.GetQueuedDestination=function()error('unknown queue')end",
                   'UnitManager.GetQueuedDestination=function()return false end',
                   'UnitManager.GetQueuedDestination=function()return {}end',
                   'UnitManager.GetQueuedDestination=function()return nil,2350 end',
                   'UnitManager.GetQueuedDestination=function()return nil,nil end')
        for change in changes:
            with self.subTest(change=change):
                self.setUp(); self.lua.execute(change); self.c.RunNow()
                self.assertEqual(self.requests(), [])
                self.assertNotIn('脚本错误', self.c.GetStatus())

    def test_queue_appearing_during_native_qualification_prevents_writer(self):
        for operation in ('MOVE_TO', 'BUILD_IMPROVEMENT', 'BUILD_IMPROVEMENT_ADJACENT', 'REPAIR', 'SKIP_TURN'):
            with self.subTest(operation=operation):
                self.setUp()
                self.lua.execute('''
UnitManager.CanStartOperation=function(unit,op,...)
 assert(unit==TestWorld.objects.builder)
 TestWorld.queuedDestination=2350;return true
end
''')
                self.assertFalse(self.write(operation)[0])
                self.assertEqual(self.requests(), [])
                self.assertEqual(self.w.queuedDestination, 2350)

    def test_last_queue_read_stops_only_the_new_unsent_proposal(self):
        self.lua.execute('''
TestWorld.queueReads=0
UnitManager.GetQueuedDestination=function(unit)
 assert(unit==TestWorld.objects.builder)
 TestWorld.queueReads=TestWorld.queueReads+1
 if TestWorld.queueReads>=3 then return 2350 end
 return nil
end
''')
        self.assertFalse(self.write()[0])
        self.assertEqual(self.w.queueReads, 3)
        self.assertEqual(self.requests(), [])
        self.assertIsNone(self.private.Pending()[3])

    def test_queued_standby_added_during_native_qualification_is_not_sent(self):
        self.lua.execute('''
UnitManager.CanStartOperation=function(unit,op,...)
 assert(op==17);TestWorld.queuedDestination=2350;return true
end
''')
        self.assertFalse(self.private.Standby(self.w.objects.builder))
        self.assertEqual(self.requests(), [])
        self.assertEqual(self.w.queuedDestination, 2350)

    def test_an_existing_unresolved_pending_record_is_never_cleared(self):
        self.g.PrivatePending = self.private.Pending()
        self.lua.execute("PrivatePending[3]={id='old-unknown',kind='MOVE_TO',from=42,plot=2350};TestWorld.queuedDestination=2350")
        self.assertFalse(self.write()[0])
        self.assertEqual(self.requests(), [])
        self.assertEqual(self.private.Pending()[3].id, 'old-unknown')
        self.assertEqual(self.w.queuedDestination, 2350)

    def test_unrelated_guard_scope_does_not_query_or_grant_military_actions(self):
        self.lua.execute("TestWorld.queueReads=0;UnitManager.GetQueuedDestination=function()TestWorld.queueReads=TestWorld.queueReads+1;error('unrelated')end")
        for kind in ('UNIT_TRADER', 'UNIT_MISSIONARY', 'UNIT_NATURALIST', 'UNIT_WARRIOR'):
            self.assertTrue(self.private.Queue(self.w.objects.builder, kind))
        self.assertEqual(self.w.queueReads, 0)
        self.assertFalse(self.g.BaiqiPolicy.ActionAllowed('UNIT_WARRIOR', 'MOVE_TO'))

    def test_original_nil_only_return_count_semantics_are_preserved(self):
        for expression in ('return', 'return nil'):
            with self.subTest(expression=expression):
                self.lua.execute('UnitManager.GetQueuedDestination=function()' + expression + ' end')
                self.assertTrue(self.private.Queue(self.w.objects.builder, 'UNIT_BUILDER'))
                self.assertTrue(self.private.Queue(self.w.objects.settler, 'UNIT_SETTLER'))

    def test_engine_queue_completion_permits_fresh_work_at_observed_destination(self):
        self.w.queuedDestination = 43
        self.c.RunNow()
        self.assertEqual(self.requests(), [])
        self.lua.execute('''
TestWorld.builderPlot=43;TestWorld.queuedDestination=nil;TestWorld.turn=2
local original=UnitManager.CanStartOperation
UnitManager.CanStartOperation=function(unit,op,...)
 if op==UnitOperationTypes.BUILD_IMPROVEMENT then return true end
 return original(unit,op,...)
end
''')
        self.c.RunNow()
        self.assertEqual(self.requests(), [(3, 12)])


if __name__ == '__main__':
    unittest.main()
