from pathlib import Path
import unittest
from lupa.lua53 import LuaRuntime

ROOT = Path(__file__).resolve().parents[1]


class LazySnapshotTests(unittest.TestCase):
    def setUp(self):
        self.lua = LuaRuntime(unpack_returned_tuples=True)
        for name in ('tests/lua/mock_world.lua', 'tests/lua/mock_trade.lua',
                     'mod/Baiqi/Lua/BaiqiConfig.lua', 'mod/Baiqi/Lua/BaiqiPolicy.lua',
                     'mod/Baiqi/Lua/BaiqiPlanner.lua'):
            self.lua.execute((ROOT / name).read_text(encoding='utf-8'))
        self.private = self.lua.execute(
            (ROOT / 'mod/Baiqi/Lua/BaiqiController.lua').read_text(encoding='utf-8')
            + '\nreturn {Pending=function() return pendingUnits end, Evaluated=function() return unitEvaluated end}\n')
        self.w = self.lua.globals().TestWorld
        self.c = self.lua.globals().BaiqiController
        self.lua.execute('''
TestWorld.queues[66]={{ProjectType='PROJECT_TEST'}}
TestWorld.queues[67]={{ProjectType='PROJECT_TEST'}}
local w=TestWorld; w.formationReads=0; w.positionReads=0
local u=w.objects.trader; local formation,x=u.GetFormationUnitCount,u.GetX
u.GetFormationUnitCount=function(self) w.formationReads=w.formationReads+1;return formation(self) end
u.GetX=function(self) w.positionReads=w.positionReads+1;return x(self) end
''')
        self.c.RunNow(False)

    def mark_evaluated(self):
        self.private.Evaluated()['4:42:2'] = True

    def enable_standby(self):
        self.lua.execute('''
GameInfo.UnitOperations={UNITOPERATION_SKIP_TURN={Hash=17}}
TestWorld.objects.trader.IsReadyToSelect=function() return true end
TestWorld.objects.trader.IsReadyToMove=function() return true end
''')

    def test_evaluated_civilian_skips_snapshot_when_standby_binding_unavailable(self):
        self.mark_evaluated()
        self.c.RunNow()
        self.assertEqual(self.w.formationReads, 0)
        self.assertGreater(self.w.positionReads, 0)
        self.assertEqual(len(self.w.unitRequests), 0)

    def test_pending_move_retains_receipt_and_skips_snapshot(self):
        self.lua.globals().Pending = self.private.Pending()
        self.lua.execute("Pending[4]={id='pending',kind='MOVE_TO',from=42,moves=2,elapsed=0}")
        self.c.RunNow()
        self.assertIsNotNone(self.private.Pending()[4])
        self.assertEqual(self.w.formationReads, 0)
        self.assertGreater(self.w.positionReads, 0)
        self.assertEqual(len(self.w.unitRequests), 0)

    def test_native_standby_rechecks_snapshot_twice_and_preserves_final_guard(self):
        for mutate in (False, True):
            with self.subTest(mutate=mutate):
                self.setUp()
                self.mark_evaluated()
                self.enable_standby()
                if mutate:
                    self.lua.execute('''
local original=UnitManager.CanStartOperation
UnitManager.CanStartOperation=function(unit,op,...)
 local ok=original(unit,op,...)
 if op==17 then TestWorld.tradeFormation=2 end
 return ok
end
''')
                self.c.RunNow()
                self.assertEqual(self.w.formationReads, 2)
                self.assertEqual(len(self.w.unitRequests), 0 if mutate else 1)
                if not mutate:
                    self.assertEqual((self.w.unitRequests[1].unit,self.w.unitRequests[1].op),(4,17))

    def test_fresh_position_key_replans_after_actual_move(self):
        self.mark_evaluated()
        self.w.traderPlot = 43
        self.c.RunNow()
        self.assertIsNotNone(self.private.Evaluated()['4:43:2'])
        self.assertGreater(self.w.formationReads, 0)
