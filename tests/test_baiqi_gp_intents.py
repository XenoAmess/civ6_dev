"""Actual Gameplay journal authorizes the actual Controller command consumer."""
import unittest
import test_baiqi_scientist as fixture
from gp_intent_harness import ROOT, install_gp_bridge

KEY = 'BAIQI_GREAT_PERSON_INTENTS_V1'


class GreatPersonIntentTests(unittest.TestCase):
    def setUp(self):
        fixture.BaiqiScientistTests.setUp(self)
        self.lua.execute('TestWorld.objects.city:GetBuildQueue().HasBeenPlaced=function() return false end')
        self.w.scientistPlot = 43
        self.h = self.lua.globals().TestBridge
        self.bridge = self.lua.globals().ExposedMembers.BaiqiGreatPersonIntentBridge

    def entry(self):
        return self.h.store[KEY].operations['4']

    def reload_contexts(self):
        self.c.Shutdown()
        saved = self.h.Copy(self.h.store)
        install_gp_bridge(self.lua, saved)
        self.h = self.lua.globals().TestBridge
        self.bridge = self.lua.globals().ExposedMembers.BaiqiGreatPersonIntentBridge
        self.lua.execute((ROOT/'mod/Baiqi/Lua/BaiqiController.lua').read_text(encoding='utf-8'))
        self.c = self.lua.globals().BaiqiController

    def test_core_receipt_exists_before_native_command_despite_stale_ui_property(self):
        self.lua.execute('''
local original=UnitManager.RequestCommand
UnitManager.RequestCommand=function(unit,...)
 local saved=TestBridge.store.BAIQI_GREAT_PERSON_INTENTS_V1
 assert(saved.operations['4'].stage=='ARMED' and saved.operations['4'].charges==1)
 assert(Players[7]:GetProperty('BAIQI_GREAT_PERSON_INTENTS_V1')==nil)
 assert(TestBridge.core.Players[7].IsHuman and TestBridge.core.PlayerConfigurations[7].IsHuman==nil)
 assert(TestBridge.core.Players[7]:GetUnits():FindID(4).GetUnitType==nil)
 return original(unit,...)
end
''')
        self.c.RunNow()
        self.assertEqual(len(self.w.commandRequests), 1)
        self.assertEqual(self.entry().token, 'gp:7:1')

    def test_reloaded_core_and_ui_never_repeat_unknown_activation_or_move_unit(self):
        self.c.RunNow()
        self.reload_contexts()
        for _ in range(3):
            self.w.turn += 1
            self.c.RunNow()
            self.c.Update(3600)
        self.assertEqual((len(self.w.commandRequests), len(self.w.unitRequests)), (1, 0))
        self.assertEqual(self.entry().stage, 'ARMED')

    def test_real_charge_decrease_can_authorize_one_distinct_next_intent(self):
        self.w.scientistCharges = 3
        self.c.RunNow()
        first = self.entry().token
        self.w.scientistCharges = 2
        self.c.RunNow()
        self.assertEqual(len(self.w.commandRequests), 2)
        self.assertNotEqual(self.entry().token, first)
        self.assertEqual((self.entry().charges, self.entry().sequence), (2, 2))
        self.c.Update(3600)
        self.assertEqual(len(self.w.commandRequests), 2)
        self.w.scientistCharges = 0
        self.c.RunNow()
        self.assertEqual((self.entry().stage, len(self.w.commandRequests)), ('OBSERVED', 2))

    def test_event_without_decreased_live_charge_cannot_release_another_intent(self):
        self.w.scientistCharges = 3
        self.c.RunNow()
        self.w.FireActivation(7, 4, 905, 770)
        self.c.RunNow()
        self.assertTrue(self.entry().eventSeen)
        self.assertEqual(self.entry().stage, 'ARMED')
        self.reload_contexts()
        self.w.turn += 1
        self.c.RunNow()
        self.assertEqual((len(self.w.commandRequests), len(self.w.unitRequests)), (1, 0))

    def test_missing_unit_without_event_is_unknown_after_reload(self):
        self.c.RunNow()
        self.w.withScientist = False
        self.reload_contexts()
        self.assertEqual(self.bridge.Inspect(7, 4)[0], 'ARMED')
        self.assertEqual(self.entry().stage, 'ARMED')

    def test_native_exception_preserves_receipt_and_other_city_production_continues(self):
        self.lua.execute("UnitManager.RequestCommand=function() error('native outcome unknown') end")
        self.c.RunNow()
        self.assertEqual(self.entry().stage, 'ARMED')
        self.assertTrue(any('great_person_command_unknown' in line for line in self.logs))
        self.w.queueSize = 0
        self.c.RefreshProduction()
        self.c.RunNow()
        self.assertEqual(len(self.w.cityRequests), 1, self.logs)
        self.assertFalse(any('|error|' in line for line in self.logs), self.logs)
        self.reload_contexts()
        self.c.RunNow()
        self.assertEqual(len(self.w.commandRequests), 0)

    def test_post_grant_formation_change_holds_receipt_without_command_or_fallback_skip(self):
        self.lua.execute('''
local bridge=ExposedMembers.BaiqiGreatPersonIntentBridge
local original=bridge.Prepare
bridge.Prepare=function(...)
 local granted,token,reason=original(...)
 TestWorld.scientistFormation=2
 return granted,token,reason
end
''')
        self.c.RunNow()
        self.assertEqual(self.entry().stage, 'ARMED')
        self.assertEqual((len(self.w.commandRequests), len(self.w.unitRequests)), (0, 0))
        self.w.scientistFormation = 1
        self.w.turn += 1
        self.c.RunNow()
        self.assertEqual((len(self.w.commandRequests), len(self.w.unitRequests)), (0, 0))

    def test_unconfirmed_property_write_never_grants_native_command(self):
        self.h.allowWrite = False
        self.c.RunNow()
        self.assertEqual(len(self.w.commandRequests), 0)
        self.assertIsNone(self.entry())

    def test_property_exception_never_stops_other_city_production(self):
        self.h.writeError = True
        self.c.RunNow()
        self.w.queueSize = 0
        self.c.RefreshProduction()
        self.c.RunNow()
        self.assertEqual((len(self.w.commandRequests), len(self.w.cityRequests)), (0, 1), self.logs)

    def test_corrupt_saved_journal_remains_identical_and_other_city_still_works(self):
        self.lua.execute("TestBridge.store.BAIQI_GREAT_PERSON_INTENTS_V1={version=9,private_unknown='retain'}")
        self.c.RunNow()
        self.w.queueSize = 0
        self.c.RefreshProduction()
        self.c.RunNow()
        self.assertEqual((len(self.w.commandRequests), len(self.w.unitRequests), len(self.w.cityRequests)), (0, 0, 1), self.logs)
        self.assertEqual(self.h.store[KEY].private_unknown, 'retain')
        self.assertEqual(self.h.writes, 1)  # Initial empty bootstrap only.

    def test_legacy_existing_charged_person_is_persistently_held_before_movement(self):
        self.h.store[KEY] = None
        self.h.FireBootstrap()
        self.assertEqual(self.entry().stage, 'LEGACY_UNKNOWN')
        self.w.scientistPlot = 42
        self.c.RunNow()
        self.reload_contexts()
        self.c.RunNow()
        self.assertEqual((len(self.w.commandRequests), len(self.w.unitRequests)), (0, 0))

    def test_reused_native_find_slot_and_oversized_id_cannot_receive_grant(self):
        self.w.scientistID, self.w.findScientistAlias = 99, True
        self.assertFalse(self.bridge.Prepare(7, 4, 'UNIT_GREAT_SCIENTIST', 5, 70, 1, 3, 3)[0])
        self.assertFalse(self.bridge.Prepare(7, 9007199254740991, 'UNIT_GREAT_SCIENTIST', 5, 70, 1, 3, 3)[0])
        self.assertIsNone(self.entry())

    def test_owner_leader_multiplayer_and_inactive_guards_reject_prepare(self):
        for expression in (
            "TestWorld.scientistOwner=8",
            "PlayerConfigurations[7].GetLeaderTypeName=function() return 'LEADER_TRAJAN' end",
            "GameConfiguration.IsAnyMultiplayer=function() return true end",
            "Players[7].IsTurnActive=function() return false end",
        ):
            with self.subTest(expression=expression):
                self.setUp()
                self.lua.execute(expression)
                self.assertFalse(self.bridge.Prepare(7, 4, 'UNIT_GREAT_SCIENTIST', 5, 70, 1, 3, 3)[0])
                self.assertIsNone(self.entry())

    def test_invalid_saved_schema_is_preserved_and_denies_real_consumer(self):
        corruptions = (
            "s.owner=8", "s.extra='unknown'", "s.operations['4'].extra=true",
            "s.operations['4'].unitID=5", "s.operations['04']=s.operations['4'];s.operations['4']=nil",
            "s.operations['4'].charges=0", "s.operations['4'].sequence=0",
            "s.operations['4'].token='gp:7:99'", "s.operations['4'].turn=math.huge",
            "s.operations['4'].eventSeen=1", "s.operations['4'].stage='READY'",
            "s.operations['5']=TestBridge.Copy(s.operations['4']);s.operations['5'].unitID=5",
        )
        for mutate in corruptions:
            with self.subTest(mutate=mutate):
                self.setUp()
                self.c.RunNow()
                self.lua.execute('local s=TestBridge.store.BAIQI_GREAT_PERSON_INTENTS_V1;'+mutate)
                writes = self.h.writes
                self.reload_contexts()
                self.c.RunNow()
                self.assertEqual(len(self.w.commandRequests), 1)
                self.assertEqual(self.h.writes, 0)
                self.assertGreaterEqual(writes, 2)


if __name__ == '__main__':
    unittest.main()
