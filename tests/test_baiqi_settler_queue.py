"""Known queued destinations reject new commands, including after a durable ACK."""
from pathlib import Path
import unittest
from lupa.lua51 import LuaRuntime

ROOT=Path(__file__).resolve().parents[1]


class SettlerQueueTests(unittest.TestCase):
    def setUp(self):
        self.lua=LuaRuntime(unpack_returned_tuples=True)
        for name in ('tests/lua/mock_world.lua','tests/lua/mock_movement.lua',
                     'tests/lua/mock_path_ranking.lua','mod/Baiqi/Lua/BaiqiConfig.lua',
                     'mod/Baiqi/Lua/BaiqiPolicy.lua','mod/Baiqi/Lua/BaiqiPlanner.lua',
                     'mod/Baiqi/Lua/BaiqiController.lua'):
            self.lua.execute((ROOT/name).read_text(encoding='utf-8'))
        self.w=self.lua.globals().TestWorld
        self.w.withBuilder,self.w.withSettler=False,True
        self.c=self.lua.globals().BaiqiController

    def ops(self):return [(a.unit,a.op)for a in self.w.unitRequests.values()]

    def test_existing_queue_blocks_move_and_preserves_original_destination(self):
        for dest in (0,43):
            with self.subTest(destination=dest):
                self.setUp();self.w.queuedDestination=dest;self.c.RunNow()
                self.assertEqual(self.ops(),[])
                self.assertEqual(self.w.queuedDestination,dest)
                self.assertIsNone(self.w.settlementBank.operations['2'])

    def test_existing_queue_blocks_found_before_journal_prepare(self):
        self.w.withCity=False;self.w.queuedDestination=43
        self.c.RunNow()
        self.assertEqual(self.ops(),[])
        self.assertIsNone(self.w.settlementBank.operations['2'])
        self.assertEqual(self.w.settlementBank.serial,0)

    def test_existing_queue_cannot_be_replaced_by_skip(self):
        self.lua.execute('TestWorld.settlementRecommendations={};TestWorld.queuedDestination=43')
        self.c.RunNow()
        self.assertEqual(self.ops(),[])
        self.assertEqual(self.w.queuedDestination,43)

    def test_missing_or_failed_queue_query_does_not_authorize_any_order(self):
        for change in ('UnitManager.GetQueuedDestination=nil',
                       "UnitManager.GetQueuedDestination=function()error('QUEUE_UNKNOWN')end",
                       'UnitManager.GetQueuedDestination=function()return nil,43 end'):
            with self.subTest(change=change):
                self.setUp();self.lua.execute(change);self.c.RunNow()
                self.assertEqual(self.ops(),[])
                self.assertNotIn('脚本错误',self.c.GetStatus())

    def test_queue_appearing_in_qualification_blocks_before_arming(self):
        self.w.withCity=False
        self.lua.execute('UnitManager.CanStartOperation=function(u,op,...)if op==UnitOperationTypes.FOUND_CITY then TestWorld.queuedDestination=43 end;return true end')
        self.c.RunNow()
        self.assertEqual(self.ops(),[])
        self.assertIsNone(self.w.settlementBank.operations['2'])

    def test_queue_appearing_after_commit_retains_armed_and_never_emits_or_replays(self):
        self.w.withCity=False
        self.lua.execute('''local b=ExposedMembers.BaiqiSettlementIntentBridge;local original=b.Commit
            b.Commit=function(...)local a,t=original(...);TestWorld.queuedDestination=43;return a,t end''')
        self.c.RunNow()
        self.assertEqual(self.ops(),[])
        record=self.w.settlementBank.operations['2']
        self.assertEqual(record.stage,'ARMED')
        token=record.token
        self.c.RunNow();self.w.turn=2;self.c.RunNow()
        self.assertEqual(self.ops(),[])
        self.assertEqual(self.w.settlementBank.operations['2'].token,token)
        self.assertEqual(self.w.queuedDestination,43)

    def test_nil_queue_preserves_normal_move_and_starting_capital(self):
        self.c.RunNow();self.assertEqual(self.ops(),[(2,10)])
        self.setUp();self.w.withCity=False;self.c.RunNow()
        self.assertEqual(self.ops(),[(2,11)])

    def test_builder_unknown_queue_also_blocks_new_orders(self):
        self.w.withSettler,self.w.withBuilder=False,True
        self.lua.execute("UnitManager.GetQueuedDestination=function()error('UNRELATED_QUEUE')end")
        self.c.RunNow()
        self.assertEqual(self.ops(),[])


if __name__=='__main__':unittest.main()
