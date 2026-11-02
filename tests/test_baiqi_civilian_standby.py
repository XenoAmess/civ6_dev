"""Real controller+Core journals with native-only ready/HOLD binding fixture."""
import unittest
import test_baiqi_missionary as missionary_fixture
from religious_intent_harness import ROOT


class StandbyTests(unittest.TestCase):
    def setUp(self):
        missionary_fixture.MissionaryTests.setUp(self)
        self.lua.execute((ROOT / 'tests/lua/mock_civilian_standby.lua').read_text(encoding='utf-8'))

    def tearDown(self):
        missionary_fixture.MissionaryTests.tearDown(self)

    def entry(self):
        return missionary_fixture.MissionaryTests.entry(self)

    def reload_contexts(self):
        missionary_fixture.MissionaryTests.reload_contexts(self)

    def skips(self):
        return [v for v in self.w.unitRequests.values() if v.op == 745019656]

    def test_unknown_receipt_is_retained_while_idle_unit_waits_once(self):
        self.c.RunNow()
        token = self.entry().token
        self.c.Update(3)
        self.assertEqual(len(self.skips()), 1, self.logs)
        self.assertEqual((self.entry().stage, self.entry().token), ('ARMED', token))
        self.assertEqual((self.w.spreadCharges, self.w.missionaryMoves), (3, 4))
        self.assertEqual(self.w.activity, 75236491)
        self.reload_contexts()
        self.c.Update(3)
        self.assertEqual((len(self.skips()), len(self.w.spreadRequests)), (1, 1))
        self.w.turn += 1
        self.w.standbyReady, self.w.activity = True, 1797587246
        self.c.Update(3)
        self.assertEqual((len(self.skips()), len(self.w.spreadRequests)), (2, 1))
        self.assertEqual(self.entry().token, token)

    def test_completed_ability_followed_by_native_move_refresh_waits_without_second_spread(self):
        self.w.autoSpread = True
        self.c.RunNow()
        self.c.RunNow()
        self.assertEqual((self.entry().stage, self.w.spreadCharges), ('OBSERVED', 2))
        self.w.missionaryMoves = 4
        self.c.RunNow()
        self.assertEqual((len(self.skips()), len(self.w.spreadRequests)), (1, 1))
        self.assertEqual((self.w.spreadCharges, self.w.missionaryMoves), (2, 4))

    def test_legacy_unknown_waits_without_rewriting_or_replaying_receipt(self):
        self.h.store['BAIQI_RELIGIOUS_INTENTS_V1'] = None
        self.h.FireBootstrap()
        token = self.entry().token
        self.c.RunNow()
        self.assertEqual((len(self.skips()), len(self.w.spreadRequests)), (1, 0))
        self.assertEqual((self.entry().stage, self.entry().token), ('LEGACY_UNKNOWN', token))
        self.assertEqual((self.w.spreadCharges, self.w.missionaryMoves), (3, 4))

    def test_ordinary_movement_pending_is_not_replaced_by_standby(self):
        self.w.secondCity, self.w.cityMajority = True, 1
        self.c.RunNow()
        self.c.Update(.4)
        self.assertEqual(len(self.skips()), 0, self.logs)
        self.assertEqual(len(self.w.unitRequests), 1)
        self.assertEqual(self.w.unitRequests[1].op, 10)

    def test_core_busy_processing_or_missing_readers_defer_all_writes(self):
        for code in ('TestWorld.busy=true', 'TestWorld.processing=true',
                     'UI.IsGameCoreBusy=nil', 'UI.IsProcessingMessages=nil'):
            with self.subTest(code=code):
                self.setUp()
                self.lua.execute(code)
                self.w.queueSize = 0
                self.c.RunNow()
                self.c.Update(3)
                self.assertFalse(self.c.IsAvailable())
                self.assertEqual((len(self.w.cityRequests), len(self.w.unitRequests), len(self.w.spreadRequests)), (0, 0, 0))
                self.assertIsNone(self.entry())

    def test_core_becomes_busy_after_grant_then_safe_wait_preserves_unknown(self):
        self.lua.execute('''
local bridge=ExposedMembers.BaiqiReligiousIntentBridge
local original=bridge.Prepare
bridge.Prepare=function(...)
 local granted,token,reason=original(...)
 assert(granted==true)
 TestWorld.busy=true
 return granted,token,reason
end
''')
        self.c.RunNow()
        self.assertEqual(self.entry().stage, 'ARMED')
        self.assertEqual((len(self.skips()), len(self.w.spreadRequests)), (0, 0))
        self.w.busy = False
        self.c.Update(3)
        self.assertEqual((len(self.skips()), len(self.w.spreadRequests)), (1, 0))
        self.assertEqual(self.entry().stage, 'ARMED')

    def test_nonwhitelisted_or_unknown_formation_readiness_or_activity_never_waits(self):
        cases = ('TestWorld.missionaryFormation=2', 'TestWorld.missionaryFormation=nil',
                 'TestWorld.missionaryType=61', 'TestWorld.missionaryType=62', 'TestWorld.missionaryType=63',
                 'TestWorld.objects.missionary.IsReadyToSelect=nil', 'TestWorld.standbyReady=false',
                 'UnitManager.GetActivityType=nil', 'TestWorld.activity=75236491')
        for code in cases:
            with self.subTest(code=code):
                self.setUp()
                self.c.RunNow()
                self.lua.execute(code)
                self.c.Update(3)
                self.assertEqual((len(self.skips()), len(self.w.spreadRequests)), (0, 1), self.logs)
                self.assertEqual(self.entry().stage, 'ARMED')

    def test_standby_exception_is_unknown_and_not_retried_same_turn(self):
        self.w.throwSkip = True
        self.c.RunNow()
        self.c.Update(3)
        self.c.Update(3)
        self.c.RunNow()
        self.assertEqual((len(self.skips()), len(self.w.spreadRequests)), (1, 1))
        self.assertEqual((self.entry().stage, self.w.spreadCharges), ('ARMED', 3))
        self.assertTrue(any('standby_unknown' in line for line in self.logs))

    def test_native_eligibility_callback_cannot_change_identity_owner_type_formation_or_core_state(self):
        mutations = ('TestWorld.missionaryID=99;TestWorld.recycledFind=true',
                     'TestWorld.missionaryOwner=8', 'TestWorld.missionaryType=61',
                     'TestWorld.missionaryFormation=2', 'TestWorld.busy=true',
                     'TestWorld.processing=true', 'TestWorld.strategic=false')
        for mutation in mutations:
            with self.subTest(mutation=mutation):
                self.setUp()
                self.c.RunNow()
                token = self.entry().token
                self.assertEqual(len(self.w.spreadRequests), 1)
                self.lua.execute('''
TestWorld.skipHookCalls=0
TestWorld.onCanSkip=function()
 TestWorld.skipHookCalls=TestWorld.skipHookCalls+1
''' + mutation + '\nend')
                self.c.Update(3)
                self.assertEqual(self.w.skipHookCalls, 1, self.logs)
                self.assertEqual((len(self.skips()), len(self.w.unitRequests), len(self.w.spreadRequests)), (0, 0, 1))
                self.assertEqual((self.entry().unitID, self.entry().stage, self.entry().token, self.entry().charges), (4, 'ARMED', token, 3))

    def test_observation_only_update_keeps_actual_confirmation_without_new_order(self):
        self.w.autoSpread = True
        self.c.RunNow()
        self.c.Update(3, False)
        self.assertEqual((self.entry().stage, self.w.spreadCharges), ('OBSERVED', 2))
        self.w.missionaryMoves = 4
        self.c.Update(3, False)
        self.assertEqual((len(self.skips()), len(self.w.spreadRequests)), (0, 1))
        self.c.Update(3, True)
        self.assertEqual((len(self.skips()), len(self.w.spreadRequests)), (1, 1))

    def test_guard_false_throw_or_missing_callback_fails_closed_for_new_orders(self):
        for code in ('function() return false end', "function() error('unavailable native phase') end", 'nil'):
            with self.subTest(code=code):
                self.setUp()
                self.lua.execute('BaiqiController.SetTurnGuard(' + code + ')')
                self.c.RunNow()
                self.c.Update(3)
                self.assertFalse(self.c.IsAvailable())
                self.assertEqual((len(self.skips()), len(self.w.spreadRequests)), (0, 0))
                self.assertIsNone(self.entry())

    def test_native_callback_phase_loss_prevents_standby_and_preserves_intent(self):
        self.lua.execute('TestWorld.phaseReady=true;BaiqiController.SetTurnGuard(function() return TestWorld.phaseReady end)')
        self.c.RunNow()
        token = self.entry().token
        self.lua.execute('TestWorld.phaseHookCalls=0;TestWorld.onCanSkip=function() TestWorld.phaseHookCalls=TestWorld.phaseHookCalls+1;TestWorld.phaseReady=false end')
        self.c.Update(3)
        self.assertEqual(self.w.phaseHookCalls, 1)
        self.assertEqual((len(self.skips()), len(self.w.spreadRequests)), (0, 1))
        self.assertEqual((self.entry().stage, self.entry().token), ('ARMED', token))

    def test_city_native_eligibility_callback_phase_loss_prevents_production(self):
        self.w.withMissionary, self.w.queueSize = False, 0
        self.lua.execute('''
TestWorld.phaseReady=true;TestWorld.cityPhaseHookCalls=0
BaiqiController.SetTurnGuard(function() return TestWorld.phaseReady end)
CityManager.CanStartOperation=function(...)
 TestWorld.cityPhaseHookCalls=TestWorld.cityPhaseHookCalls+1
 TestWorld.phaseReady=false
 return true
end
''')
        self.c.RunNow()
        self.assertGreaterEqual(self.w.cityPhaseHookCalls, 1)
        self.assertEqual(len(self.w.cityRequests), 0)


if __name__ == '__main__':
    unittest.main()
