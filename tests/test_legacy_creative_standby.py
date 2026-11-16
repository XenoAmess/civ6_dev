"""Legacy creator sleep preserves real Core unknown intent; not a spent-work claim."""
from pathlib import Path
import unittest
from lupa.lua51 import LuaRuntime as L51
from lupa.lua53 import LuaRuntime as L53
from creative_intent_harness import install_creative_bridge

ROOT = Path(__file__).resolve().parents[1]
KEY = 'BAIQI_CREATIVE_INTENTS_V1'


class LegacyCreativeStandbyTests(unittest.TestCase):
    def fixture(self, runtime=L53, legacy=True, kind=8):
        lua = runtime(unpack_returned_tuples=True)
        for name in ('mock_world', 'mock_scientist', 'mock_creative'):
            lua.execute((ROOT/f'tests/lua/{name}.lua').read_text(encoding='utf-8'))
        w = lua.globals().TestWorld
        w.SetCreativeKind(kind)
        if not legacy:
            w.withScientist = False
        install_creative_bridge(lua)
        w.withScientist = True
        lua.execute('''
local w=TestWorld;local u=w.objects.player:GetUnits():FindID(4)
w.activity=1797587246;w.ready=true;w.sleepLegal=true;w.sleepCalls=0;w.sleepRequests={};w.nativePending=false
ActivityTypes={ACTIVITY_AWAKE=1797587246,ACTIVITY_HOLD=75236491,ACTIVITY_SLEEP=38434027}
u.IsReadyToSelect=function()return w.ready end
u.HasPendingOperations=function()return w.nativePending end
UnitManager.GetActivityType=function()return w.activity end
UnitManager.GetQueuedDestination=function()return w.nativeDestination end
GameInfo.UnitOperations={UNITOPERATION_SKIP_TURN={Hash=745019656},UNITOPERATION_SLEEP={Hash=-41338758}}
local can=UnitManager.CanStartOperation
UnitManager.CanStartOperation=function(u,op,...)
 if op==-41338758 then w.sleepCalls=w.sleepCalls+1;if w.sleepHook then w.sleepHook(w.sleepCalls)end;return w.sleepLegal end
 if op==745019656 then return w.ready and w.activity==1797587246 end
 return can(u,op,...)
end
local request=UnitManager.RequestOperation
UnitManager.RequestOperation=function(u,op,params)
 if op==-41338758 then
  w.sleepRequests[#w.sleepRequests+1]={id=u:GetID(),op=op}
  if w.throwSleep then error('unknown sleep outcome')end
  w.activity=38434027;w.ready=false;return
 end
 if op==745019656 then w.unitRequests[#w.unitRequests+1]={unit=u:GetID(),op=op};return end
 return request(u,op,params)
end
''')
        for name in ('BaiqiConfig', 'BaiqiPolicy', 'BaiqiPlanner'):
            lua.execute((ROOT/f'mod/Baiqi/Lua/{name}.lua').read_text(encoding='utf-8'))
        access = lua.execute((ROOT/'mod/Baiqi/Lua/BaiqiController.lua').read_text(encoding='utf-8')
                             + '\nreturn {Standby=RequestCivilianStandby,Pending=function()return pendingUnits end}\n')
        c = lua.globals().BaiqiController
        logs = []
        lua.globals().print = lambda *v: logs.append(' '.join(map(str, v)))
        c.RunNow(False)
        return lua, w, c, lua.globals().TestBridge, access, logs

    def test_legacy_three_creator_classes_sleep_once_without_work_or_journal_change(self):
        for engine in (L51, L53):
            for kind in (6, 7, 8):
                with self.subTest(engine=engine.__module__, kind=kind):
                    lua, w, c, h, access, logs = self.fixture(engine, kind=kind)
                    token, writes = h.store[KEY].operations['4'].token, h.writes
                    c.RunNow()
                    self.assertEqual([(r.id, r.op) for r in w.sleepRequests.values()], [(4, -41338758)], logs)
                    self.assertEqual((len(w.unitRequests), len(w.commandRequests)), (0, 0))
                    self.assertEqual((h.store[KEY].operations['4'].stage, h.store[KEY].operations['4'].token, h.writes), ('LEGACY_UNKNOWN', token, writes))
                    c.RunNow()
                    self.assertEqual(len(w.sleepRequests), 1)

    def test_zero_charge_open_creator_still_creates_and_armed_never_gets_sleep(self):
        for engine in (L51, L53):
            lua, w, c, h, access, logs = self.fixture(engine, legacy=False)
            w.scientistPlot = 43
            c.RunNow()
            self.assertEqual((len(w.commandRequests), len(w.sleepRequests)), (1, 0), logs)
            c.Update(3)
            self.assertEqual((h.store[KEY].operations['4'].stage, len(w.sleepRequests)), ('ARMED', 0))

    def test_unavailable_sleep_retains_original_legal_skip(self):
        for change in ('TestWorld.sleepLegal=false', 'GameInfo.UnitOperations.UNITOPERATION_SLEEP=nil'):
            for engine in (L51, L53):
                lua, w, c, h, access, logs = self.fixture(engine)
                lua.execute(change)
                c.RunNow()
                self.assertEqual((len(w.sleepRequests), [r.op for r in w.unitRequests.values()]), (0, [745019656]))

    def test_local_or_native_pending_and_ambiguous_queue_cannot_be_replaced(self):
        changes = ('TestWorld.nativePending=true', 'TestWorld.nativePending=nil',
                   'TestWorld.nativeDestination=43',
                   'TestWorld.objects.player:GetUnits():FindID(4).HasPendingOperations=function()return false,nil end',
                   'UnitManager.GetQueuedDestination=function()return nil,nil end')
        for engine in (L51, L53):
            for change in changes:
                lua, w, c, h, access, logs = self.fixture(engine)
                lua.execute(change)
                self.assertFalse(access.Standby(w.objects.player.GetUnits(w.objects.player).FindID(None, 4)))
                self.assertEqual((len(w.sleepRequests), len(w.unitRequests)), (0, 0))
            lua, w, c, h, access, logs = self.fixture(engine)
            access.Pending()[4] = lua.table_from(dict(id='held', kind='CREATE_GREAT_WORK', persistent=True))
            self.assertFalse(access.Standby(w.objects.player.GetUnits(w.objects.player).FindID(None, 4)))
            self.assertEqual(access.Pending()[4].id, 'held')
            self.assertEqual(len(w.sleepRequests), 0)

    def test_native_check_mutations_close_sleep_without_alternate_order(self):
        mutations = ('TestWorld.scientistOwner=8', 'TestWorld.scientistFormation=2',
                     'TestWorld.scientistFormation=nil', 'TestWorld.busy=true',
                     'TestWorld.strategic=false', 'TestWorld.nativePending=true',
                     'TestWorld.scientistCharges=1', 'TestWorld.scientistPlot=43',
                     'GameInfo.UnitOperations.UNITOPERATION_SLEEP.Hash=99',
                     'UnitManager.RequestOperation=function()error("foreign writer")end',
                     'TestBridge.store.BAIQI_CREATIVE_INTENTS_V1.operations["4"].stage="ARMED"')
        for engine in (L51, L53):
            for boundary in (1, 2):
                for change in mutations:
                    with self.subTest(engine=engine.__module__, boundary=boundary, change=change):
                        lua, w, c, h, access, logs = self.fixture(engine)
                        lua.execute(f'TestWorld.sleepHook=function(n)if n=={boundary} then {change} end end')
                        self.assertFalse(access.Standby(w.objects.player.GetUnits(w.objects.player).FindID(None, 4)))
                        self.assertEqual((len(w.sleepRequests), len(w.unitRequests)), (0, 0))

    def test_throwing_sleep_is_unknown_and_not_retried_or_converted_to_skip(self):
        for engine in (L51, L53):
            lua, w, c, h, access, logs = self.fixture(engine)
            w.throwSleep = True
            actor = w.objects.player.GetUnits(w.objects.player).FindID(None, 4)
            self.assertTrue(access.Standby(actor))
            self.assertFalse(access.Standby(actor))
            self.assertEqual((len(w.sleepRequests), len(w.unitRequests)), (1, 0))
            self.assertEqual(h.store[KEY].operations['4'].stage, 'LEGACY_UNKNOWN')
            self.assertTrue(any('standby_unknown' in s for s in logs))
