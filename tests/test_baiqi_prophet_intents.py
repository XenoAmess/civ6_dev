"""Durable one-shot prophet permission; explicit software ports, not Native proof."""
from pathlib import Path
import unittest
from lupa.lua53 import LuaRuntime
from prophet_intent_harness import install_prophet_bridge

ROOT = Path(__file__).resolve().parents[1]
KEY = 'BAIQI_PROPHET_INTENTS_V1'


class ProphetIntentTests(unittest.TestCase):
    def setUp(self):
        self.lua = LuaRuntime(unpack_returned_tuples=True)
        self.lua.globals().print = lambda *args: None
        for name in ('tests/lua/mock_world.lua', 'tests/lua/mock_scientist.lua',
                     'tests/lua/mock_prophet.lua', 'mod/Baiqi/Lua/BaiqiConfig.lua',
                     'mod/Baiqi/Lua/BaiqiPolicy.lua'):
            self.lua.execute((ROOT/name).read_text(encoding='utf-8'))
        self.w = self.lua.globals().TestWorld
        self.w.scientistPlot = 43
        self.h = install_prophet_bridge(self.lua)
        self.bridge = self.lua.globals().ExposedMembers.BaiqiProphetIntentBridge

    def prepare(self, ident=4):
        return self.bridge.Prepare(7, ident, 4, 70, 3, 3, 0)

    def inspect(self):
        return self.bridge.Inspect(7, 4)

    def operation(self):
        return self.h.store[KEY].operations['4']

    def test_prepared_once_survives_new_gameplay_environment_without_regrant(self):
        granted, token, _ = self.prepare()
        self.assertTrue(granted)
        self.assertEqual(self.operation().stage, 'ARMED')
        self.h = install_prophet_bridge(self.lua, self.h.store, fresh=False)
        self.bridge = self.lua.globals().ExposedMembers.BaiqiProphetIntentBridge
        self.assertEqual(self.inspect()[:2], ('ARMED', token))
        self.assertFalse(self.prepare()[0])
        self.assertEqual(self.h.store[KEY].serial, 1)

    def test_zero_moves_existing_legacy_prophet_is_not_granted(self):
        self.w.scientistMoves = 0
        self.h = install_prophet_bridge(self.lua, fresh=False)
        self.bridge = self.lua.globals().ExposedMembers.BaiqiProphetIntentBridge
        self.assertEqual(self.inspect()[0], 'LEGACY_UNKNOWN')
        self.assertFalse(self.prepare()[0])

    def test_matching_event_persists_then_actual_consumption_confirms(self):
        self.assertTrue(self.prepare()[0])
        stage, token, _ = self.bridge.Observe(7, 4, 4, 70)
        self.assertEqual(stage, 'ARMED')
        self.assertTrue(self.operation().eventSeen)
        self.h = install_prophet_bridge(self.lua, self.h.store, fresh=False)
        self.bridge = self.lua.globals().ExposedMembers.BaiqiProphetIntentBridge
        self.w.withScientist = False
        self.assertEqual(self.inspect()[:2], ('OBSERVED', token))
        self.assertFalse(self.prepare()[0])

    def test_missing_unit_and_created_religion_without_matching_event_do_not_confirm(self):
        self.assertTrue(self.prepare()[0])
        self.w.withScientist = False
        self.w.createdReligion = 2
        self.assertEqual(self.inspect()[0], 'ARMED')
        self.assertFalse(self.operation().eventSeen)

    def test_alias_full_id_is_unknown_not_consumption(self):
        self.assertTrue(self.prepare()[0])
        self.w.scientistID, self.w.findScientistAlias = 65540, True
        self.w.createdReligion = 2
        self.assertEqual(self.bridge.Observe(7, 4, 4, 70)[0], 'ARMED')
        self.assertEqual(self.inspect()[0], 'ARMED')

    def test_wrong_event_identity_and_foreign_owner_leave_receipt_unchanged(self):
        self.assertTrue(self.prepare()[0])
        for args in ((8, 4, 4, 70), (7, 5, 4, 70), (7, 4, 5, 70), (7, 4, 4, 71)):
            with self.subTest(args=args):
                self.bridge.Observe(*args)
                self.assertFalse(self.operation().eventSeen)
                self.assertEqual(self.inspect()[0], 'ARMED')

    def test_corrupt_journal_is_preserved_and_never_repaired_into_grant(self):
        self.lua.execute("TestPropBridge.store['BAIQI_PROPHET_INTENTS_V1'].unexpected='keep'")
        writes = self.h.writes
        self.assertEqual(self.inspect()[0], 'UNAVAILABLE')
        self.assertFalse(self.prepare()[0])
        self.assertEqual(self.h.writes, writes)
        self.assertEqual(self.h.store[KEY].unexpected, 'keep')

    def test_lost_persist_readback_never_grants_or_retries_armed_operation(self):
        self.h.loseWriteReadback = True
        self.assertFalse(self.prepare()[0])
        self.h.loseWriteReadback = False
        self.assertEqual(self.inspect()[0], 'ARMED')
        self.assertFalse(self.prepare()[0])
        self.assertEqual(self.h.store[KEY].serial, 1)

    def test_foreign_bridge_is_preserved_without_bootstrap_write(self):
        self.h = install_prophet_bridge(self.lua, foreign=True)
        self.assertEqual(self.lua.globals().ExposedMembers.BaiqiProphetIntentBridge.marker, 'foreign')
        self.assertEqual(self.h.writes, 0)

    def test_prepare_requires_active_strategic_own_land_and_exact_argument_order(self):
        for flag in ('strategic', 'water', 'class_order'):
            with self.subTest(flag=flag):
                self.setUp()
                if flag == 'strategic':
                    self.w.strategic = False
                elif flag == 'water':
                    self.w.prophetWater = True
                args = (7, 4, 70, 4, 3, 3, 0) if flag == 'class_order' else (7, 4, 4, 70, 3, 3, 0)
                self.assertFalse(self.bridge.Prepare(*args)[0])
                self.assertEqual(self.h.store[KEY].serial, 0)

    def test_live_zero_moves_with_matching_event_and_created_religion_is_observed(self):
        self.assertTrue(self.prepare()[0])
        self.w.scientistMoves = 0
        self.w.createdReligion = 2
        self.assertEqual(self.bridge.Observe(7, 4, 4, 70)[0], 'OBSERVED')
        self.assertFalse(self.prepare()[0])

    def test_unsupported_native_id_never_enters_find_id(self):
        before=len(self.h.findIDs)
        self.assertFalse(self.prepare(2147483648)[0])
        self.assertEqual(len(self.h.findIDs),before)

    def test_observed_without_causal_event_is_malformed_not_permission(self):
        self.assertTrue(self.prepare()[0])
        self.operation().stage = 'OBSERVED'
        self.operation().eventSeen = False
        writes=self.h.writes
        self.assertEqual(self.inspect()[0], 'UNAVAILABLE')
        self.assertFalse(self.prepare()[0])
        self.assertEqual(self.h.writes,writes)


    def test_retained_offmap_identity_and_created_religion_confirm_matching_event(self):
        granted, token, _ = self.prepare()
        self.assertTrue(granted)
        self.lua.execute("""
local u=Players[7]:GetUnits():FindID(4)
u.GetX=function() return -9999 end
u.GetY=function() return -9999 end
""")
        self.w.createdReligion = 2
        self.assertEqual(self.bridge.Observe(7, 4, 4, 70)[:2], ('OBSERVED', token))
        self.assertTrue(self.operation().eventSeen)
        self.h = install_prophet_bridge(self.lua, self.h.store, fresh=False)
        self.bridge = self.lua.globals().ExposedMembers.BaiqiProphetIntentBridge
        self.assertEqual(self.inspect()[:2], ('OBSERVED', token))
        self.assertFalse(self.prepare()[0])
        self.assertEqual(self.h.store[KEY].serial, 1)

    def test_offmap_position_never_replaces_event_or_exact_identity(self):
        for kind in ('no_event', 'alias', 'owner', 'class', 'individual'):
            with self.subTest(kind=kind):
                self.setUp()
                self.assertTrue(self.prepare()[0])
                self.lua.execute("""
local u=Players[7]:GetUnits():FindID(4)
u.GetX=function() return -9999 end
u.GetY=function() return -9999 end
""")
                self.w.createdReligion = 2
                if kind == 'alias':
                    self.w.scientistID, self.w.findScientistAlias = 65540, True
                elif kind == 'owner':
                    self.w.scientistOwner = 8
                elif kind == 'class':
                    self.w.scientistClass = 5
                elif kind == 'individual':
                    self.w.scientistIndividual = 71
                if kind != 'no_event':
                    self.assertEqual(self.bridge.Observe(7, 4, 4, 70)[0], 'ARMED')
                self.assertEqual(self.inspect()[0], 'ARMED')
                self.assertFalse(self.prepare()[0])

    def test_offmap_position_cannot_get_new_permission_or_enter_map_lookup(self):
        self.lua.execute("""
local u=Players[7]:GetUnits():FindID(4)
u.GetX=function() return -9999 end
u.GetY=function() return -9999 end
TestWorld.negativeMapCalls=0
TestPropBridge.core.Map.GetPlot=function()
 TestWorld.negativeMapCalls=TestWorld.negativeMapCalls+1
 error('invalid coordinates must be rejected before native Map call')
end
""")
        self.assertFalse(self.prepare()[0])
        self.assertEqual(self.h.store[KEY].serial, 0)
        self.assertEqual(self.w.negativeMapCalls, 0)

    def test_offmap_untracked_legacy_unit_is_unavailable_without_rewriting_store(self):
        self.lua.execute("""
local u=Players[7]:GetUnits():FindID(4)
u.GetX=function() return -9999 end
u.GetY=function() return -9999 end
""")
        self.h = install_prophet_bridge(self.lua, fresh=False)
        self.bridge = self.lua.globals().ExposedMembers.BaiqiProphetIntentBridge
        self.assertEqual(self.inspect()[0], 'UNAVAILABLE')
        self.assertFalse(self.prepare()[0])
        self.assertEqual(self.h.writes, 0)
        self.assertIsNone(self.h.store[KEY])


    def test_bootstrap_reconciles_persisted_event_without_consumer_call(self):
        self.assertTrue(self.prepare()[0])
        self.assertEqual(self.bridge.Observe(7, 4, 4, 70)[0], 'ARMED')
        self.assertTrue(self.operation().eventSeen)
        self.w.withScientist = False
        self.w.createdReligion = 2
        prior = self.h.store
        self.h = install_prophet_bridge(self.lua, prior, fresh=False)
        self.bridge = self.lua.globals().ExposedMembers.BaiqiProphetIntentBridge
        op = self.h.store[KEY].operations['4']
        self.assertEqual(op.stage, 'OBSERVED')
        self.assertEqual(op.token, 'prophet:7:1')
        self.assertEqual(self.h.store[KEY].serial, 1)
        self.setUp()
        self.assertTrue(self.prepare()[0])
        self.w.withScientist = False
        self.w.createdReligion = 2
        self.h = install_prophet_bridge(self.lua, self.h.store, fresh=False)
        self.assertEqual(self.h.store[KEY].operations['4'].stage, 'ARMED')

    def test_bootstrap_alias_does_not_confirm_even_with_event_and_created_religion(self):
        self.assertTrue(self.prepare()[0])
        self.bridge.Observe(7, 4, 4, 70)
        self.w.scientistID, self.w.findScientistAlias = 65540, True
        self.w.createdReligion = 2
        self.h = install_prophet_bridge(self.lua, self.h.store, fresh=False)
        self.assertEqual(self.h.store[KEY].operations['4'].stage, 'ARMED')
        self.assertTrue(self.h.store[KEY].operations['4'].eventSeen)

    def test_bootstrap_preserves_corrupt_record_without_new_write(self):
        self.assertTrue(self.prepare()[0])
        self.bridge.Observe(7, 4, 4, 70)
        self.h.store[KEY].unexpected = 'preserve'
        self.w.withScientist = False
        self.w.createdReligion = 2
        self.h = install_prophet_bridge(self.lua, self.h.store, fresh=False)
        self.assertEqual(self.h.writes, 0)
        self.assertEqual(self.h.store[KEY].unexpected, 'preserve')
        self.assertEqual(self.h.store[KEY].operations['4'].stage, 'ARMED')

    def test_actual_registered_bootstrap_reconciles_once_without_consumer_call(self):
        self.assertTrue(self.prepare()[0])
        self.bridge.Observe(7, 4, 4, 70)
        writes = self.h.writes
        self.w.withScientist = False
        self.w.createdReligion = 2
        self.h.FireBootstrap()
        self.assertEqual(self.h.store[KEY].operations['4'].stage, 'OBSERVED')
        self.assertEqual(self.h.writes, writes + 1)
        self.h.FireBootstrap()
        self.assertEqual(self.h.writes, writes + 1)


if __name__ == '__main__':
    unittest.main()
