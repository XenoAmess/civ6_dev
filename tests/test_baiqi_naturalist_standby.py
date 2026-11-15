"""Native SKIP-rejected naturalist must wait without replacing an active task."""
import os
from pathlib import Path
import unittest
from lupa.lua53 import LuaRuntime
from naturalist_ui_harness import ROOT, install_naturalist_bridge


class NaturalistStandbyTests(unittest.TestCase):
    def setUp(self):
        self.lua = LuaRuntime(unpack_returned_tuples=True)
        for name in ('mock_world', 'mock_missionary', 'mock_naturalist', 'mock_civilian_standby'):
            self.lua.execute((ROOT / f'tests/lua/{name}.lua').read_text(encoding='utf-8'))
        self.logs = []
        self.lua.globals().print = lambda *v: self.logs.append(' '.join(map(str, v)))
        install_naturalist_bridge(self.lua)
        self.lua.execute('''
local w=TestWorld
w.skipLegal=false;w.parkCandidates={};w.sleepLegal=true;w.sleepCalls=0;w.sleepRequests={}
w.nativePending=false;w.purchaseStage='OPEN'
w.objects.missionary.HasPendingOperations=function()return w.nativePending end
UnitManager.GetQueuedDestination=function()return w.nativeDestination end
GameInfo.UnitOperations.UNITOPERATION_SLEEP={Hash=-41338758}
ExposedMembers.BaiqiNaturalistPurchaseBridge={version=1,marker='baiqi-naturalist-purchase-v1',
 Inspect=function()return w.purchaseStage end}
local can=UnitManager.CanStartOperation
UnitManager.CanStartOperation=function(u,op,...)
 if op==-41338758 then w.sleepCalls=w.sleepCalls+1;if w.sleepHook then w.sleepHook(w.sleepCalls)end;return w.sleepLegal end
 return can(u,op,...)
end
local request=UnitManager.RequestOperation
UnitManager.RequestOperation=function(u,op,p)
 if op==-41338758 then
  w.sleepRequests[#w.sleepRequests+1]={id=u:GetID(),op=op}
  if w.throwSleep then error('unknown sleep outcome')end
  w.activity=38434027;w.standbyReady=false;return
 end
 return request(u,op,p)
end
''')
        for name in ('BaiqiConfig', 'BaiqiPolicy', 'BaiqiPlanner', 'BaiqiHeritageCandidates', 'BaiqiHeritageActions'):
            self.lua.execute((ROOT / f'mod/Baiqi/Lua/{name}.lua').read_text(encoding='utf-8'))
        source = Path(os.environ.get('BAIQI_NATURALIST_STANDBY_CONTROLLER', str(ROOT / 'mod/Baiqi/Lua/BaiqiController.lua')))
        self.private = self.lua.execute(source.read_text(encoding='utf-8')
            + '\nreturn {Standby=RequestCivilianStandby,Pending=function()return pendingUnits end}\n')
        self.w = self.lua.globals().TestWorld
        self.c = self.lua.globals().BaiqiController
        self.c.RunNow(False)

    def wait(self):
        return self.private.Standby(self.w.objects.missionary)

    def test_no_park_real_controller_sleeps_once_without_player_fill(self):
        self.c.RunNow()
        self.assertEqual([(r.id, r.op) for r in self.w.sleepRequests.values()], [(4, -41338758)], self.logs)
        self.assertEqual((len(self.w.parkRequests), len(self.w.unitRequests)), (0, 0))
        self.c.RunNow()
        self.assertEqual(len(self.w.sleepRequests), 1)

    def test_skip_preferred_and_does_not_read_sleep_receipts(self):
        self.w.skipLegal = True
        self.lua.execute("ExposedMembers.BaiqiNaturalistPurchaseBridge=nil;ExposedMembers.BaiqiNaturalistIntentBridge=nil")
        self.assertTrue(self.wait())
        self.assertEqual((len(self.w.sleepRequests), len(self.w.unitRequests)), (0, 1))

    def test_non_naturalist_does_not_gain_sleep(self):
        self.lua.execute("GameInfo.Units[60].UnitType='UNIT_MISSIONARY'")
        self.assertFalse(self.wait())
        self.assertEqual(len(self.w.sleepRequests), 0)

    def test_unknown_skip_is_not_false_and_cannot_authorize_sleep(self):
        self.lua.execute('local can=UnitManager.CanStartOperation;UnitManager.CanStartOperation=function(u,op,...)if op==745019656 then return nil end;return can(u,op,...)end')
        self.assertFalse(self.wait())
        self.assertEqual(self.w.sleepCalls, 0)

    def test_unknown_or_armed_purchase_refuses_without_journal_changes(self):
        for stage in ('ARMED', 'UNKNOWN', 'UNAVAILABLE'):
            with self.subTest(stage=stage):
                self.setUp();self.w.purchaseStage = stage
                writes = self.lua.globals().TestParkBridge.writes
                self.assertFalse(self.wait())
                self.assertEqual(len(self.w.sleepRequests), 0)
                self.assertEqual(self.lua.globals().TestParkBridge.writes, writes)

    def test_pending_local_record_preserved(self):
        self.private.Pending()[4] = self.lua.table_from(dict(id='old', kind='DESIGNATE_PARK', persistent=True))
        self.assertFalse(self.wait())
        self.assertEqual(self.private.Pending()[4].id, 'old')
        self.assertEqual(len(self.w.sleepRequests), 0)

    def test_queue_unknown_or_pending_never_replaced(self):
        for mutation in ('TestWorld.nativePending=true', 'TestWorld.nativePending=nil',
                         'TestWorld.objects.missionary.HasPendingOperations=nil',
                         "TestWorld.objects.missionary.HasPendingOperations=function()error('unavailable')end",
                         'TestWorld.nativeDestination=43', 'UnitManager.GetQueuedDestination=nil',
                         "UnitManager.GetQueuedDestination=function()error('unavailable')end",
                         'UnitManager.GetQueuedDestination=function()return nil,nil end',
                         'UnitManager.GetQueuedDestination=function()return nil,43 end'):
            with self.subTest(mutation=mutation):
                self.setUp();self.lua.execute(mutation)
                self.assertFalse(self.wait())
                self.assertEqual(len(self.w.sleepRequests), 0)

    def test_changes_at_either_native_sleep_check_refuse_request(self):
        for boundary in (1, 2):
            for mutation in ('TestWorld.nativePending=true', 'TestWorld.nativeDestination=43',
                             'TestWorld.missionaryOwner=8', 'TestWorld.missionaryFormation=2',
                             'TestWorld.busy=true', 'TestWorld.strategic=false',
                             "TestWorld.purchaseStage='UNKNOWN'",
                             'GameInfo.UnitOperations.UNITOPERATION_SLEEP.Hash=99',
                             'UnitManager.RequestOperation=function()error("rebound writer")end'):
                with self.subTest(boundary=boundary,mutation=mutation):
                    self.setUp();self.lua.execute(f'TestWorld.sleepHook=function(n)if n=={boundary} then {mutation} end end')
                    self.assertFalse(self.wait())
                    self.assertEqual(len(self.w.sleepRequests), 0)

    def test_rejected_sleep_does_not_fall_through_to_another_action(self):
        self.w.sleepLegal = False
        self.assertFalse(self.wait())
        self.assertEqual((len(self.w.sleepRequests),len(self.w.unitRequests),len(self.w.parkRequests)), (0,0,0))

    def test_unknown_request_is_logged_and_never_retried_same_turn(self):
        self.w.throwSleep = True
        self.assertTrue(self.wait())
        self.assertFalse(self.wait())
        self.assertEqual(len(self.w.sleepRequests), 1)
        self.assertTrue(any('standby_unknown' in line for line in self.logs))

    def test_park_receipt_missing_unknown_or_armed_is_preserved(self):
        for stage in ('ARMED','UNKNOWN','UNAVAILABLE'):
            with self.subTest(stage=stage):
                self.setUp()
                self.lua.execute(f"ExposedMembers.BaiqiNaturalistIntentBridge.Inspect=function()return '{stage}'end")
                self.assertFalse(self.wait())
                self.assertEqual(len(self.w.sleepRequests),0)
        for mutation in ('ExposedMembers.BaiqiNaturalistIntentBridge=nil',
                         "ExposedMembers.BaiqiNaturalistIntentBridge.Inspect=function()error('unknown')end",
                         'ExposedMembers.BaiqiNaturalistPurchaseBridge=nil'):
            with self.subTest(mutation=mutation):
                self.setUp();self.lua.execute(mutation)
                self.assertFalse(self.wait())
                self.assertEqual(len(self.w.sleepRequests),0)

    def test_new_park_site_next_turn_still_uses_real_park_permission(self):
        self.c.RunNow()
        self.assertEqual(len(self.w.sleepRequests),1)
        self.w.turn += 1
        self.w.parkCandidates = self.lua.table_from([42])
        self.c.RunNow()
        self.assertEqual((len(self.w.parkRequests),len(self.w.sleepRequests)),(1,1),self.logs)

    def test_invalid_sleep_row_and_non_true_legality_refuse(self):
        for mutation in ('GameInfo.UnitOperations.UNITOPERATION_SLEEP=nil',
                         'GameInfo.UnitOperations.UNITOPERATION_SLEEP.Hash=0/0',
                         'TestWorld.sleepLegal=nil', 'TestWorld.sleepLegal=1'):
            with self.subTest(mutation=mutation):
                self.setUp();self.lua.execute(mutation)
                self.assertFalse(self.wait())
                self.assertEqual(len(self.w.sleepRequests),0)


if __name__ == '__main__':
    unittest.main()
