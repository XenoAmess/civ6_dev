"""Legacy district people wait without replaying their unknown activation."""
from pathlib import Path
import unittest
from lupa.lua51 import LuaRuntime as L51
from lupa.lua53 import LuaRuntime as L53
from gp_intent_harness import install_gp_bridge

ROOT = Path(__file__).resolve().parents[1]
CONTROLLER = ROOT/'mod/Baiqi/Lua/BaiqiController.lua'
KEY = 'BAIQI_GREAT_PERSON_INTENTS_V1'


class LegacyDistrictStandbyTests(unittest.TestCase):
    def fixture(self, engine=L53, kind='MERCHANT', legacy=True):
        lua = engine(unpack_returned_tuples=True)
        logs = []
        lua.globals().print = lambda *v: logs.append(' '.join(map(str, v)))
        for name in ('mock_world', 'mock_scientist'):
            lua.execute((ROOT/f'tests/lua/{name}.lua').read_text(encoding='utf-8'))
        lua.execute("""
local w=TestWorld;local u=w.objects.player:GetUnits():FindID(4)
w.scientistCharges=3;w.scientistMoves=4;w.ready=true;w.activity=1797587246
w.sleepLegal=true;w.sleepCalls=0;w.sleepRequests={};w.nativePending=false
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
""")
        lua.execute(f"GameInfo.Units[3].UnitType='UNIT_GREAT_{kind}';GameInfo.GreatPersonIndividuals[70].GreatPersonClassType='GREAT_PERSON_CLASS_{kind}';GameInfo.GreatPersonClasses[5].GreatPersonClassType='GREAT_PERSON_CLASS_{kind}'")
        w = lua.globals().TestWorld
        if not legacy:
            w.withScientist = False
        install_gp_bridge(lua)
        w.withScientist = True
        for name in ('BaiqiConfig', 'BaiqiPolicy', 'BaiqiPlanner'):
            lua.execute((ROOT/f'mod/Baiqi/Lua/{name}.lua').read_text(encoding='utf-8'))
        access = lua.execute(CONTROLLER.read_text(encoding='utf-8') + '\nreturn {Standby=RequestCivilianStandby,Pending=function()return pendingUnits end}\n')
        c = lua.globals().BaiqiController
        c.RunNow(False)
        return lua, w, c, lua.globals().TestBridge, access, logs

    def test_three_charged_classes_sleep_once_keep_real_legacy_journal(self):
        for engine in (L51, L53):
            for kind in ('MERCHANT', 'SCIENTIST', 'ENGINEER'):
                with self.subTest(engine=engine.__module__, kind=kind):
                    lua, w, c, h, access, logs = self.fixture(engine, kind)
                    token, writes = h.store[KEY].operations['4'].token, h.writes
                    c.RunNow()
                    self.assertEqual([(r.id, r.op) for r in w.sleepRequests.values()], [(4, -41338758)], logs)
                    self.assertEqual((len(w.unitRequests), len(w.commandRequests)), (0, 0))
                    self.assertEqual((h.store[KEY].operations['4'].stage, h.store[KEY].operations['4'].token, h.writes, w.scientistCharges), ('LEGACY_UNKNOWN', token, writes, 3))
                    c.RunNow()
                    self.assertEqual(len(w.sleepRequests), 1)

    def test_open_and_armed_keep_activation_protocol(self):
        for engine in (L51, L53):
            lua, w, c, h, access, logs = self.fixture(engine, legacy=False)
            w.scientistPlot = 43
            c.RunNow()
            self.assertEqual((len(w.commandRequests), len(w.sleepRequests)), (1, 0), logs)
            c.Update(3)
            self.assertEqual((h.store[KEY].operations['4'].stage, len(w.sleepRequests)), ('ARMED', 0))

    def test_native_queue_or_local_intent_never_replaced(self):
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
            access.Pending()[4] = lua.table_from(dict(id='held', kind='ACTIVATE_GREAT_PERSON', persistent=True))
            self.assertFalse(access.Standby(w.objects.player.GetUnits(w.objects.player).FindID(None, 4)))
            self.assertEqual((access.Pending()[4].id, len(w.sleepRequests)), ('held', 0))

    def test_both_native_checks_revalidate_receipt_identity_and_permissions(self):
        changes = ('TestWorld.scientistOwner=8', 'TestWorld.scientistFormation=2',
                   'TestWorld.scientistFormation=nil', 'TestWorld.busy=true',
                   'TestWorld.strategic=false', 'TestWorld.nativePending=true',
                   'TestWorld.scientistCharges=2', 'TestWorld.scientistCharges=0',
                   'TestWorld.scientistIndividual=999', 'TestWorld.scientistPlot=43',
                   'GameInfo.UnitOperations.UNITOPERATION_SLEEP.Hash=99',
                   'UnitManager.RequestOperation=function()error("foreign writer")end',
                   'TestBridge.store.BAIQI_GREAT_PERSON_INTENTS_V1.operations["4"].stage="ARMED"',
                   'TestBridge.store.BAIQI_GREAT_PERSON_INTENTS_V1.operations["4"].token="gp:7:2"')
        for engine in (L51, L53):
            for boundary in (1, 2):
                for change in changes:
                    with self.subTest(engine=engine.__module__, boundary=boundary, change=change):
                        lua, w, c, h, access, logs = self.fixture(engine)
                        lua.execute(f'TestWorld.sleepHook=function(n)if n=={boundary} then {change} end end')
                        self.assertFalse(access.Standby(w.objects.player.GetUnits(w.objects.player).FindID(None, 4)))
                        self.assertEqual((len(w.sleepRequests), len(w.unitRequests)), (0, 0))

    def test_missing_or_rejected_sleep_retains_original_skip(self):
        for engine in (L51, L53):
            for change in ('TestWorld.sleepLegal=false', 'GameInfo.UnitOperations.UNITOPERATION_SLEEP=nil'):
                lua, w, c, h, access, logs = self.fixture(engine)
                lua.execute(change)
                c.RunNow()
                self.assertEqual((len(w.sleepRequests), [r.op for r in w.unitRequests.values()]), (0, [745019656]))

    def test_unknown_sleep_never_repeated_or_converted_to_skip(self):
        for engine in (L51, L53):
            lua, w, c, h, access, logs = self.fixture(engine)
            w.throwSleep = True
            actor = w.objects.player.GetUnits(w.objects.player).FindID(None, 4)
            self.assertTrue(access.Standby(actor))
            self.assertFalse(access.Standby(actor))
            self.assertEqual((len(w.sleepRequests), len(w.unitRequests)), (1, 0))
            self.assertEqual(h.store[KEY].operations['4'].stage, 'LEGACY_UNKNOWN')

    def test_slept_legacy_survives_context_reload_without_new_order(self):
        for engine in (L51, L53):
            lua, w, c, h, access, logs = self.fixture(engine)
            c.RunNow()
            token = h.store[KEY].operations['4'].token
            c.Shutdown()
            install_gp_bridge(lua, h.Copy(h.store))
            lua.execute(CONTROLLER.read_text(encoding='utf-8'))
            lua.globals().BaiqiController.RunNow()
            h = lua.globals().TestBridge
            self.assertEqual((len(w.sleepRequests), len(w.unitRequests), len(w.commandRequests)), (1, 0, 0))
            self.assertEqual((h.store[KEY].operations['4'].stage, h.store[KEY].operations['4'].token), ('LEGACY_UNKNOWN', token))
