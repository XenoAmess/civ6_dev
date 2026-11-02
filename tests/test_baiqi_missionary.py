"""Actual Core receipt/Controller/UI guard; no religious combat automation."""
import unittest
from lupa.lua53 import LuaRuntime
from religious_intent_harness import ROOT, install_religious_bridge

KEY = 'BAIQI_RELIGIOUS_INTENTS_V1'


class MissionaryTests(unittest.TestCase):
    def setUp(self):
        self.lua = LuaRuntime(unpack_returned_tuples=True)
        for name in ('mock_world', 'mock_missionary'):
            self.lua.execute((ROOT / f'tests/lua/{name}.lua').read_text(encoding='utf-8'))
        self.logs = []
        self.lua.globals().print = lambda *args: self.logs.append(' '.join(map(str, args)))
        install_religious_bridge(self.lua)
        for name in ('BaiqiConfig', 'BaiqiPolicy', 'BaiqiPlanner', 'BaiqiController'):
            self.lua.execute((ROOT / f'mod/Baiqi/Lua/{name}.lua').read_text(encoding='utf-8'))
        self.w = self.lua.globals().TestWorld
        self.h = self.lua.globals().TestRelBridge
        self.c = self.lua.globals().BaiqiController
        self.bridge = self.lua.globals().ExposedMembers.BaiqiReligiousIntentBridge
        self.w.withMissionary = True

    def tearDown(self):
        self.assertFalse(any('|error|' in line for line in self.logs), self.logs)

    def entry(self):
        return self.h.store[KEY].operations['4']

    def reload_contexts(self):
        self.c.Shutdown()
        saved = self.h.Copy(self.h.store)
        install_religious_bridge(self.lua, saved)
        self.h = self.lua.globals().TestRelBridge
        self.bridge = self.lua.globals().ExposedMembers.BaiqiReligiousIntentBridge
        self.lua.execute((ROOT / 'mod/Baiqi/Lua/BaiqiController.lua').read_text(encoding='utf-8'))
        self.c = self.lua.globals().BaiqiController

    def test_actual_core_receipt_precedes_exact_native_operation_without_target_params(self):
        self.lua.execute('''
TestWorld.onSpread=function(unit,op,params)
 local entry=TestRelBridge.store.BAIQI_RELIGIOUS_INTENTS_V1.operations['4']
 assert(entry.stage=='ARMED' and entry.charges==3 and entry.cityID==66)
 assert(Players[7]:GetProperty('BAIQI_RELIGIOUS_INTENTS_V1')==nil)
 assert(unit.GetReligion==nil and UnitOperationTypes.SPREAD_RELIGION==nil)
 local native=TestRelBridge.core.Players[7]:GetUnits():FindID(4)
 assert(native.GetSpreadCharges==nil and native.GetUnitType==nil and native:GetReligion():GetSpreadCharges()==3)
 assert(params==nil)
end
''')
        self.c.RunNow()
        self.assertEqual(len(self.w.spreadRequests), 1, self.logs)
        self.assertEqual(self.entry().token, 'religion:7:1')
        self.assertEqual(self.w.spreadRequests[1].op, 1592408602)
        self.assertEqual(len(self.w.unitRequests), 0)

    def test_actual_charge_decrease_confirms_and_next_turn_gets_distinct_receipt(self):
        self.w.autoSpread = True
        self.c.RunNow()
        self.c.RunNow()
        self.assertEqual((self.entry().stage, self.w.spreadCharges, self.w.missionaryMoves), ('OBSERVED', 2, 0))
        first = self.entry().token
        self.w.turn += 1
        self.w.missionaryMoves = 4
        self.c.RunNow()
        self.assertEqual(len(self.w.spreadRequests), 2)
        self.assertNotEqual(self.entry().token, first)
        self.assertEqual((self.entry().charges, self.entry().sequence), (2, 2))

    def test_unknown_native_outcome_survives_core_and_ui_reload_without_moves_or_spread(self):
        self.c.RunNow()
        self.reload_contexts()
        for _ in range(3):
            self.w.turn += 1
            self.c.Update(3600)
        self.assertEqual((len(self.w.spreadRequests), len(self.w.unitRequests)), (1, 0))
        self.assertEqual(self.entry().stage, 'ARMED')
        self.assertIsNone(self.bridge.Observe)

    def test_last_charge_missing_unit_is_unknown_not_a_fabricated_receipt(self):
        self.w.spreadCharges = 1
        self.c.RunNow()
        self.w.withMissionary = False
        self.reload_contexts()
        self.w.turn += 1
        self.c.RunNow()
        self.assertEqual(self.bridge.Inspect(7, 4)[0], 'ARMED')
        self.assertEqual(len(self.w.spreadRequests), 1)

    def test_property_failure_or_unknown_schema_never_grants_and_city_production_continues(self):
        for mode in ('allowWrite', 'writeError', 'corrupt'):
            with self.subTest(mode=mode):
                self.setUp()
                if mode == 'corrupt':
                    self.lua.execute("TestRelBridge.store.BAIQI_RELIGIOUS_INTENTS_V1={version=99,unknown='retain'}")
                elif mode == 'allowWrite':
                    self.h.allowWrite = False
                else:
                    self.h.writeError = True
                self.c.RunNow()
                self.w.queueSize = 0
                self.c.RefreshProduction()
                self.c.RunNow()
                self.assertEqual((len(self.w.spreadRequests), len(self.w.cityRequests)), (0, 1), self.logs)
                if mode == 'corrupt':
                    self.assertEqual(self.h.store[KEY].unknown, 'retain')

    def test_legacy_existing_unit_holds_before_any_movement(self):
        self.h.store[KEY] = None
        self.h.FireBootstrap()
        self.assertEqual(self.entry().stage, 'LEGACY_UNKNOWN')
        self.c.RunNow()
        self.reload_contexts()
        self.w.turn += 1
        self.c.RunNow()
        self.assertEqual((len(self.w.spreadRequests), len(self.w.unitRequests)), (0, 0))

    def test_native_exception_preserves_intent_and_does_not_stop_other_city_work(self):
        self.w.throwSpread = True
        self.c.RunNow()
        self.assertEqual(self.entry().stage, 'ARMED')
        self.assertTrue(any('missionary_operation_unknown' in line for line in self.logs))
        self.w.queueSize = 0
        self.c.RefreshProduction()
        self.c.RunNow()
        self.assertEqual(len(self.w.cityRequests), 1)
        self.reload_contexts()
        self.w.turn += 1
        self.c.RunNow()
        self.assertEqual(len(self.w.spreadRequests), 1)

    def test_foreign_religion_city_owner_majority_visibility_and_formation_deny_spread(self):
        for field, value in (('unitReligion', 2), ('ownReligion', -1), ('cityOwner', 8),
                             ('cityMajority', 1), ('visible', False), ('revealed', False),
                             ('missionaryFormation', 2), ('missingCoreMoves', True)):
            with self.subTest(field=field):
                self.setUp()
                setattr(self.w, field, value)
                self.c.RunNow()
                self.assertEqual(len(self.w.spreadRequests), 0, self.logs)
                self.assertIsNone(self.entry())

    def test_recycled_native_slot_and_oversized_id_do_not_receive_grants(self):
        self.w.missionaryID, self.w.recycledFind = 99, True
        self.assertFalse(self.bridge.Prepare(7, 4, 1, 3, 2, 3, 66)[0])
        self.assertFalse(self.bridge.Prepare(7, 9007199254740991, 1, 3, 2, 3, 66)[0])
        self.assertIsNone(self.entry())
        self.assertTrue(all(value <= 2147483647 for value in self.h.findIDs.values()))

    def test_post_grant_changes_never_emit_or_replay_spread(self):
        for field, value, restore in (('missionaryFormation', 2, 1), ('cityOwner', 8, 7),
                                      ('cityID', 99, 66), ('missionaryType', 61, 60)):
            with self.subTest(field=field):
                self.setUp()
                self.lua.globals().PostGrantField = field
                self.lua.globals().PostGrantValue = value
                self.lua.execute('''
local bridge=ExposedMembers.BaiqiReligiousIntentBridge
local original=bridge.Prepare
TestWorld.grantHookCalls=0
bridge.Prepare=function(...)
 local granted,token,reason=original(...)
 assert(granted==true)
 TestWorld.grantHookCalls=TestWorld.grantHookCalls+1
 TestWorld[PostGrantField]=PostGrantValue
 return granted,token,reason
end
''')
                self.c.RunNow()
                self.assertEqual(self.w.grantHookCalls, 1)
                self.assertEqual(self.entry().stage, 'ARMED')
                self.assertEqual((len(self.w.spreadRequests), len(self.w.unitRequests)), (0, 0))
                setattr(self.w, field, restore)
                self.reload_contexts()
                self.w.turn += 1
                self.c.RunNow()
                self.c.Update(3600)
                self.assertEqual(self.entry().stage, 'ARMED')
                self.assertEqual((len(self.w.spreadRequests), len(self.w.unitRequests)), (0, 0))

    def test_religious_combat_types_receive_no_background_operations(self):
        for kind in (61, 62, 63):
            with self.subTest(kind=kind):
                self.setUp()
                self.w.missionaryType = kind
                self.c.RunNow()
                self.c.Update(3600)
                self.assertEqual((len(self.w.spreadRequests), len(self.w.unitRequests)), (0, 0))

    def test_exact_256_record_boundary_is_valid_but_new_actor_and_257th_record_are_denied(self):
        self.lua.execute('''
local j=TestRelBridge.core.BaiqiReligiousJournal
local s={version=1,owner=7,serial=256,operations={}}
for i=1,256 do
 s.operations[tostring(i)]={token='religion:7:'..i,sequence=i,unitID=i,unitType='UNIT_MISSIONARY',
  religion=1,charges=3,x=2,y=3,cityID=66,cityX=2,cityY=3,turn=1,stage='ARMED'}
end
assert(j.Validate(s,7)==true)
TestRelBridge.store.BAIQI_RELIGIOUS_INTENTS_V1=s
TestWorld.missionaryID=400
''')
        self.c.RunNow()
        self.assertEqual(len(self.w.spreadRequests), 0)
        self.assertEqual(self.h.store[KEY].serial, 256)
        self.assertIsNone(self.h.store[KEY].operations['400'])
        self.lua.execute('''
local s=TestRelBridge.store.BAIQI_RELIGIOUS_INTENTS_V1
s.serial=257
s.operations['257']={token='religion:7:257',sequence=257,unitID=257,unitType='UNIT_MISSIONARY',
 religion=1,charges=3,x=2,y=3,cityID=66,cityX=2,cityY=3,turn=1,stage='ARMED'}
assert(TestRelBridge.core.BaiqiReligiousJournal.Validate(s,7)==false)
''')
        self.reload_contexts()
        self.w.turn += 1
        self.c.RunNow()
        self.assertEqual((len(self.w.spreadRequests), self.h.writes), (0, 0))

    def test_route_keeps_same_owned_city_purpose_across_steps(self):
        self.w.secondCity = True
        self.w.cityMajority = 1
        self.c.RunNow()
        self.assertEqual((self.w.unitRequests[1].op, self.w.unitRequests[1].params[14]), (10, 3), self.logs)
        self.w.missionaryPlot = 43
        self.w.missionaryMoves = 3
        self.w.cityMajority = -1
        self.c.RunNow()
        self.assertEqual(self.w.unitRequests[2].params[14], 4, self.logs)
        self.w.missionaryPlot = 44
        self.w.missionaryMoves = 2
        self.c.RunNow()
        self.assertEqual((len(self.w.spreadRequests), self.entry().cityID), (1, 67), self.logs)

    def test_journal_schema_corruptions_retain_raw_data_and_deny_actual_consumer(self):
        mutations = ("s.extra=true", "s.owner=8", "s.operations['4'].religion=-1",
                     "s.operations['4'].cityX=99", "s.operations['4'].charges=0",
                     "s.operations['4'].stage='READY'", "s.operations['4'].sequence=0",
                     "s.operations['4'].token='wrong'", "s.operations['4'].extra={}",
                     "s.operations['04']=s.operations['4'];s.operations['4']=nil")
        for mutation in mutations:
            with self.subTest(mutation=mutation):
                self.setUp()
                self.c.RunNow()
                self.lua.execute('local s=TestRelBridge.store.BAIQI_RELIGIOUS_INTENTS_V1;' + mutation)
                self.reload_contexts()
                self.w.turn += 1
                self.c.RunNow()
                self.assertEqual(len(self.w.spreadRequests), 1)
                self.assertEqual(self.h.writes, 0)


if __name__ == '__main__':
    unittest.main()
