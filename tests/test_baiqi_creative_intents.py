"""Actual zero-charge creator command, native event and persistence consumers."""
from pathlib import Path
import unittest
from lupa.lua53 import LuaRuntime
from creative_intent_harness import install_creative_bridge

ROOT = Path(__file__).resolve().parents[1]
KEY = 'BAIQI_CREATIVE_INTENTS_V1'


class CreativeIntentTests(unittest.TestCase):
    def setUp(self):
        self.lua = LuaRuntime(unpack_returned_tuples=True)
        for name in ('mock_world', 'mock_scientist', 'mock_creative'):
            self.lua.execute((ROOT/f'tests/lua/{name}.lua').read_text(encoding='utf-8'))
        self.w = self.lua.globals().TestWorld
        self.w.withScientist = False
        install_creative_bridge(self.lua)
        self.w.withScientist = True
        for name in ('BaiqiConfig', 'BaiqiPolicy', 'BaiqiPlanner', 'BaiqiController'):
            self.lua.execute((ROOT/f'mod/Baiqi/Lua/{name}.lua').read_text(encoding='utf-8'))
        self.c = self.lua.globals().BaiqiController
        self.h = self.lua.globals().TestBridge
        self.bridge = self.lua.globals().ExposedMembers.BaiqiCreativeIntentBridge
        self.w.scientistPlot = 43
        self.logs = []
        self.lua.globals().print = lambda *args: self.logs.append(' '.join(map(str, args)))

    def entry(self):
        return self.h.store[KEY].operations['4']

    def reload_contexts(self):
        self.c.Shutdown()
        stored = self.h.Copy(self.h.store)
        install_creative_bridge(self.lua, stored)
        self.h = self.lua.globals().TestBridge
        self.bridge = self.lua.globals().ExposedMembers.BaiqiCreativeIntentBridge
        self.lua.execute((ROOT/'mod/Baiqi/Lua/BaiqiController.lua').read_text(encoding='utf-8'))
        self.c = self.lua.globals().BaiqiController

    def test_each_zero_charge_class_has_fresh_durable_grant_before_native_command_with_ui_lag(self):
        for kind in (6, 7, 8):
            with self.subTest(kind=kind):
                self.setUp()
                self.w.SetCreativeKind(kind)
                self.lua.execute('''
local original=UnitManager.RequestCommand
UnitManager.RequestCommand=function(unit,...)
 local op=TestBridge.store.BAIQI_CREATIVE_INTENTS_V1.operations['4']
 assert(op.stage=='ARMED' and op.token=='creative:7:1')
 assert(unit:GetGreatPerson():GetActionCharges()==0)
 assert(Players[7]:GetProperty('BAIQI_CREATIVE_INTENTS_V1')==nil)
 assert(TestBridge.core.Cities.GetCityInPlot(2,3):GetBuildings().GetGreatWorkInSlot==nil)
 assert(ExposedMembers.BaiqiCreativeIntentBridge.Observe==nil)
 return original(unit,...)
end
''')
                self.c.RunNow()
                self.assertEqual(len(self.w.commandRequests), 1, self.logs)
                self.assertEqual(self.entry().stage, 'ARMED')

    def test_unknown_armed_survives_both_context_reloads_without_command_movement_or_skip(self):
        self.c.RunNow()
        token = self.entry().token
        self.reload_contexts()
        for _ in range(3):
            self.w.turn += 1
            self.c.RunNow()
            self.c.Update(3600)
        self.assertEqual((len(self.w.commandRequests), len(self.w.unitRequests)), (1, 0))
        self.assertEqual((self.entry().stage, self.entry().token), ('ARMED', token))

    def test_ui_event_and_real_slot_without_trusted_core_event_do_not_release_intent(self):
        self.c.RunNow()
        self.w.PlaceWork(91, 0)
        self.h.FireUIWork(7, 4, 2, 3, 2, 91)
        self.c.RunNow()
        self.assertEqual(self.entry().stage, 'ARMED')
        self.assertFalse(any('|kind=CREATE_GREAT_WORK|' in line for line in self.logs))
        self.reload_contexts()
        self.assertEqual(self.bridge.Inspect(7, 4)[0], 'ARMED')

    def test_core_event_persists_before_ui_slot_but_live_pending_keeps_waiting_for_ui_proof(self):
        self.c.RunNow()
        self.h.FireCoreWork(7, 4, 2, 3, 2, 91)
        self.h.FireUIWork(7, 4, 2, 3, 2, 91)
        self.assertEqual((self.entry().stage, self.entry().lastWork), ('OBSERVED', 91))
        self.c.Update(3600)
        self.assertFalse(any('|kind=CREATE_GREAT_WORK|' in line for line in self.logs))
        self.assertEqual(len(self.w.commandRequests), 1)
        self.w.PlaceWork(91, 0)
        self.c.RunNow()
        self.assertTrue(any('|kind=CREATE_GREAT_WORK|' in line for line in self.logs))

    def test_distinct_second_work_gets_new_token_and_delayed_old_event_cannot_settle_it(self):
        self.lua.execute('TestWorld.slots={-1,-1}')
        self.c.RunNow()
        first = self.entry().token
        self.w.PlaceWork(91, 0)
        self.w.FireWork(7, 4, 2, 3, 2, 91)
        self.w.turn += 1
        self.c.RunNow()
        self.assertEqual(len(self.w.commandRequests), 2)
        self.assertNotEqual(self.entry().token, first)
        self.assertEqual((self.entry().stage, self.entry().lastWork), ('ARMED', 91))
        self.h.FireCoreWork(7, 4, 2, 3, 2, 91)
        self.assertEqual(self.entry().stage, 'ARMED')
        self.lua.execute('TestWorld.slots[2]=92;TestWorld.workTypes[92]=1')
        self.w.FireWork(7, 4, 2, 3, 2, 92)
        self.c.RunNow()
        self.assertEqual((self.entry().stage, self.entry().lastWork), ('OBSERVED', 92))
        self.assertTrue(self.entry().works['91'] and self.entry().works['92'])
        self.assertEqual(len(self.w.commandRequests), 2)

    def test_observed_record_survives_reload_and_permits_next_legitimate_creation(self):
        self.lua.execute('TestWorld.slots={-1,-1}')
        self.c.RunNow()
        self.w.PlaceWork(91, 0)
        self.w.FireWork(7, 4, 2, 3, 2, 91)
        self.reload_contexts()
        self.c.RunNow()
        self.assertEqual((len(self.w.commandRequests), self.entry().sequence), (2, 2))
        self.assertTrue(self.entry().works['91'])

    def test_wrong_player_creator_coordinates_building_or_foreign_city_cannot_settle(self):
        for packet in ((8, 4, 2, 3, 2, 91), (7, 99, 2, 3, 2, 91), (7, 4, 9, 3, 2, 91),
                       (7, 4, 2, 3, 999, 91), (7, 4, 2, 3, 2, -1), (7, 4, 2, 3, 2, 1.5)):
            with self.subTest(packet=packet):
                self.setUp()
                self.c.RunNow()
                self.h.FireCoreWork(*packet)
                self.assertEqual(self.entry().stage, 'ARMED')
        self.w.cityOwner = 8
        self.h.FireCoreWork(7, 4, 2, 3, 2, 91)
        self.assertEqual(self.entry().stage, 'ARMED')

    def test_missing_unit_alone_never_releases_but_exact_trusted_event_can_finish_consumed_unit(self):
        self.c.RunNow()
        self.w.withScientist = False
        self.reload_contexts()
        self.assertEqual(self.bridge.Inspect(7, 4)[0], 'ARMED')
        self.h.FireCoreWork(7, 4, 2, 3, 2, 91)
        self.assertEqual(self.entry().stage, 'OBSERVED')

    def test_native_command_exception_is_held_and_city_production_continues(self):
        self.lua.execute("UnitManager.RequestCommand=function() error('unknown native outcome') end")
        self.c.RunNow()
        self.assertEqual(self.entry().stage, 'ARMED')
        self.assertTrue(any('creative_command_unknown' in line for line in self.logs))
        self.w.queueSize = 0
        self.c.RefreshProduction()
        self.c.RunNow()
        self.assertEqual(len(self.w.cityRequests), 1, self.logs)
        self.reload_contexts()
        self.c.RunNow()
        self.assertEqual(len(self.w.commandRequests), 0)

    def test_post_grant_slot_identity_formation_position_or_native_gate_change_holds_without_fallback(self):
        for mutation in ('TestWorld.PlaceWork(91,0)', 'TestWorld.scientistFormation=2',
                         'TestWorld.scientistOwner=8', 'TestWorld.scientistID=99',
                         'TestWorld.scientistPlot=42', 'TestWorld.rejectActivation=true'):
            with self.subTest(mutation=mutation):
                self.setUp()
                self.lua.execute('''
local bridge=ExposedMembers.BaiqiCreativeIntentBridge;local original=bridge.Prepare
bridge.Prepare=function(...)
 local a,b,c=original(...)
 '''+mutation+'''
 return a,b,c
end
''')
                self.c.RunNow()
                self.assertEqual(self.entry().stage, 'ARMED')
                self.assertEqual((len(self.w.commandRequests), len(self.w.unitRequests)), (0, 0))

    def test_unconfirmed_or_throwing_property_write_cannot_grant_or_stop_city_work(self):
        for field in ('allowWrite', 'writeError'):
            with self.subTest(field=field):
                self.setUp()
                setattr(self.h, field, field == 'writeError')
                self.c.RunNow()
                self.assertIsNone(self.entry())
                self.w.queueSize = 0
                self.c.RefreshProduction()
                self.c.RunNow()
                self.assertEqual((len(self.w.commandRequests), len(self.w.cityRequests)), (0, 1))

    def test_unpersisted_native_event_cannot_release_even_if_ui_sees_real_work(self):
        self.c.RunNow()
        self.h.allowWrite = False
        self.w.PlaceWork(91, 0)
        self.w.FireWork(7, 4, 2, 3, 2, 91)
        self.assertEqual(self.entry().stage, 'ARMED')
        self.c.RunNow()
        self.assertFalse(any('|kind=CREATE_GREAT_WORK|' in line for line in self.logs))
        self.reload_contexts()
        self.assertEqual(self.entry().stage, 'ARMED')

    def test_legacy_creator_bootstraps_unknown_and_other_cities_continue(self):
        self.h.store[KEY] = None
        self.bridge.Inspect(7, 4)
        self.assertEqual(self.entry().stage, 'LEGACY_UNKNOWN')
        self.c.RunNow()
        self.w.queueSize = 0
        self.c.RefreshProduction()
        self.c.RunNow()
        self.assertEqual((len(self.w.commandRequests), len(self.w.unitRequests), len(self.w.cityRequests)), (0, 0, 1))
        self.reload_contexts()
        self.assertEqual(self.entry().stage, 'LEGACY_UNKNOWN')

    def test_corrupt_raw_journal_is_retained_without_repair_or_native_actions(self):
        self.lua.execute("TestBridge.store.BAIQI_CREATIVE_INTENTS_V1={version=9,unknown='retain'}")
        writes = self.h.writes
        self.c.RunNow()
        self.assertEqual(self.h.store[KEY].unknown, 'retain')
        self.assertEqual((len(self.w.commandRequests), len(self.w.unitRequests), self.h.writes), (0, 0, writes))

    def test_owner_leader_multiplayer_human_and_inactive_guards_deny_prepare(self):
        for mutation in ("TestWorld.scientistOwner=8", "PlayerConfigurations[7].GetLeaderTypeName=function() return 'LEADER_TRAJAN' end",
                         "GameConfiguration.IsAnyMultiplayer=function() return true end", "Players[7].IsTurnActive=function() return false end",
                         "PlayerConfigurations[7].IsHuman=function() return false end"):
            with self.subTest(mutation=mutation):
                self.setUp()
                self.lua.execute(mutation)
                self.assertFalse(self.bridge.Prepare(7, 4, 'UNIT_GREAT_WRITER', 6, 80, 3, 3)[0])
                self.assertIsNone(self.entry())

    def test_recycled_slot_and_large_engine_id_never_receive_grants(self):
        self.w.scientistID, self.w.findScientistAlias = 99, True
        self.assertFalse(self.bridge.Prepare(7, 4, 'UNIT_GREAT_WRITER', 6, 80, 3, 3)[0])
        self.assertFalse(self.bridge.Prepare(7, 9007199254740991, 'UNIT_GREAT_WRITER', 6, 80, 3, 3)[0])
        self.assertIsNone(self.entry())

    def test_another_creator_cannot_obtain_a_grant_while_first_is_unknown(self):
        self.c.RunNow()
        self.assertEqual(self.bridge.Inspect(7, 55)[0], 'BUSY')
        self.assertFalse(self.bridge.Prepare(7, 55, 'UNIT_GREAT_WRITER', 6, 80, 3, 3)[0])
        self.assertEqual(self.entry().sequence, 1)

    def test_strict_schema_rejects_malformed_receipts_and_deeply_copies_seen_works(self):
        mutations = ("s.extra=true", "s.owner=8", "op.extra=true", "op.stage='READY'", "op.token='creative:7:99'",
                     "op.sequence=0", "op.turn=math.huge", "op.unitID=0/0", "op.works={['01']=true}",
                     "op.works={['1']=false}", "op.stage='OBSERVED'", "op.works={['1']=true};op.lastWork=2")
        for mutation in mutations:
            with self.subTest(mutation=mutation):
                self.setUp()
                self.c.RunNow()
                self.lua.execute('local s=TestBridge.store.BAIQI_CREATIVE_INTENTS_V1;local op=s.operations[\'4\'];'+mutation)
                self.reload_contexts()
                self.c.RunNow()
                self.assertEqual(len(self.w.commandRequests), 1)
                self.assertEqual(self.h.writes, 0)
        self.setUp()
        self.c.RunNow()
        self.h.FireCoreWork(7, 4, 2, 3, 2, 91)
        self.lua.execute('''
local j=TestBridge.core.BaiqiCreativeJournal;local s=TestBridge.store.BAIQI_CREATIVE_INTENTS_V1
local copy=j.Clone(s,7);assert(j.Equal(copy,s,7))
copy.operations['4'].works['92']=true
assert(not s.operations['4'].works['92'] and not j.Equal(copy,s,7))
''')

    def test_schema_work_limits_full_saved_ids_and_cross_unit_uniqueness(self):
        self.c.RunNow()
        self.lua.execute('''
local j=TestBridge.core.BaiqiCreativeJournal
local s=j.Clone(TestBridge.store.BAIQI_CREATIVE_INTENTS_V1,7)
local op=s.operations['4'];op.stage='OBSERVED';op.lastWork=63
for index=0,63 do op.works[tostring(index)]=true end
assert(j.Validate(s,7))
TestBridge.store.BAIQI_CREATIVE_INTENTS_V1=j.Clone(s,7)
op.works['64']=true;assert(not j.Validate(s,7));op.works['64']=nil
local copy=j.Clone(s,7);copy.operations['4']=nil
op=copy.operations['9007199254740991'] or j.Clone(s,7).operations['4']
copy.operations['9007199254740991']=op;op.unitID=9007199254740991
assert(j.Validate(copy,7))
copy.operations['9007199254740991']=nil;op.unitID=9007199254740992
copy.operations['9007199254740992']=op;assert(not j.Validate(copy,7))
local duplicate=j.Clone(s,7);duplicate.serial=2
duplicate.operations['5']=j.Clone(s,7).operations['4']
duplicate.operations['5'].unitID=5;duplicate.operations['5'].sequence=2
duplicate.operations['5'].token='creative:7:2'
assert(not j.Validate(duplicate,7))
''')
        self.assertFalse(self.bridge.Prepare(7, 4, 'UNIT_GREAT_WRITER', 6, 80, 3, 3)[0])

    def test_schema_unit_and_serial_limits(self):
        self.c.RunNow()
        self.lua.execute('''
local j=TestBridge.core.BaiqiCreativeJournal
local original=TestBridge.store.BAIQI_CREATIVE_INTENTS_V1
local s=j.New(7);s.serial=256
for id=1,256 do
 local op=j.Clone(original,7).operations['4']
 op.unitID=id;op.sequence=id;op.token=j.Token(7,id)
 s.operations[tostring(id)]=op
end
assert(j.Validate(s,7))
s.serial=257;local op=j.Clone(original,7).operations['4']
op.unitID=257;op.sequence=257;op.token=j.Token(7,257);s.operations['257']=op
assert(not j.Validate(s,7))
local endSerial=j.Clone(original,7);endSerial.serial=2147483647
assert(j.Validate(endSerial,7))
TestBridge.store.BAIQI_CREATIVE_INTENTS_V1=endSerial
endSerial.serial=2147483648;assert(not j.Validate(endSerial,7))
''')


if __name__ == '__main__':
    unittest.main()
