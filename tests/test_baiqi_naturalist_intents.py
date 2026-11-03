from pathlib import Path
import unittest
from lupa import LuaRuntime
from naturalist_intent_harness import core_runtime, to_python

ROOT = Path(__file__).resolve().parents[1]


class NaturalistIntentTests(unittest.TestCase):
    def test_park_effect_not_unit_disappearance_completes_receipt(self):
        lua, bridge = core_runtime()
        self.assertEqual(bridge.Inspect(4, 100001)[0], 'OPEN')
        granted, token, _ = bridge.Prepare(4, 100001, 1, 8, 9)
        self.assertTrue(granted)
        self.assertEqual(token, 'park:4:1')
        lua.globals().F.missingUnit = True
        self.assertEqual(bridge.Inspect(4, 100001)[:2], ('ARMED', token))
        lua.globals().F.parkValue = True
        self.assertEqual(bridge.Inspect(4, 100001)[:2], ('OBSERVED', token))

    def test_cold_reload_preserves_unknown_and_does_not_grant_again(self):
        lua, bridge = core_runtime()
        self.assertTrue(bridge.Prepare(4, 100001, 1, 8, 9)[0])
        state = to_python(lua.globals().Stored)
        reloaded, restored = core_runtime(state)
        self.assertEqual(restored.Inspect(4, 100001)[0], 'ARMED')
        self.assertFalse(restored.Prepare(4, 100001, 1, 8, 9)[0])
        self.assertEqual(reloaded.globals().Stored.serial, 1)

    def test_malformed_existing_journal_is_preserved(self):
        for state in ('unknown-version', {'version': 99, 'owner': 4, 'serial': 0, 'operations': {}}):
            lua, bridge = core_runtime(state)
            self.assertEqual(bridge.Inspect(4, 100001)[0], 'UNAVAILABLE')
            self.assertFalse(bridge.Prepare(4, 100001, 1, 8, 9)[0])
            self.assertEqual(lua.globals().F.propertyWrites, 0)
            self.assertEqual(to_python(lua.globals().Stored), state)

    def test_formation_moves_charges_full_id_and_owner_are_fresh(self):
        for field, value in (('formation', 2), ('moves', 0), ('charges', 0),
                             ('unitID', 100002), ('unitOwner', 3), ('changeOwnerDuringRead', True),
                             ('kind', 'UNIT_APOSTLE'), ('active', False)):
            with self.subTest(field=field):
                lua, bridge = core_runtime()
                lua.globals().F[field] = value
                self.assertFalse(bridge.Prepare(4, 100001, 1, 8, 9)[0])
                self.assertEqual(lua.globals().Stored.serial, 0)

    def test_hidden_or_foreign_target_never_authorizes(self):
        for field, value in (('visible', False), ('revealed', False), ('plotOwner', 3),
                             ('parkValue', True), ('parkValue', None)):
            lua, bridge = core_runtime()
            lua.globals().F[field] = value
            lua.globals().F.forbidHiddenOwner = True
            self.assertFalse(bridge.Prepare(4, 100001, 1, 8, 9)[0])
            if field in ('visible', 'revealed'):
                self.assertEqual(lua.globals().F.ownerReads, 0)

    def test_failed_persistence_never_grants_action(self):
        lua, bridge = core_runtime()
        lua.globals().F.dropWrites = True
        self.assertEqual(bridge.Prepare(4, 100001, 1, 8, 9)[0], False)
        self.assertEqual(lua.globals().Stored.serial, 0)

    def test_one_target_cannot_have_two_armed_units(self):
        lua, bridge = core_runtime()
        self.assertTrue(bridge.Prepare(4, 100001, 1, 8, 9)[0])
        lua.globals().F.unitID = 100002
        lua.globals().F.slot = 100002
        self.assertEqual(bridge.Prepare(4, 100002, 1, 8, 9), (False, None, 'target_reserved'))
        self.assertEqual(lua.globals().Stored.serial, 1)

    def test_other_leader_modes_and_missing_configuration_do_not_grant(self):
        for field, value in (('leader', 'LEADER_GORGO'), ('multiplayer', True),
                             ('hotseat', True), ('localPlayer', 8)):
            lua, bridge = core_runtime()
            before = lua.globals().F.propertyWrites
            lua.globals().F[field] = value
            self.assertFalse(bridge.Prepare(4, 100001, 1, 8, 9)[0])
            self.assertEqual(lua.globals().F.propertyWrites, before)
        lua, bridge = core_runtime(inject_config_key=False)
        self.assertFalse(bridge.Prepare(4, 100001, 1, 8, 9)[0])
        self.assertEqual(lua.globals().F.propertyWrites, 0)


class NaturalistSnapshotTests(unittest.TestCase):
    def test_snapshot_uses_core_type_and_park_charge_api(self):
        lua, _ = core_runtime()
        read = lua.globals().BaiqiNaturalistUnit.Read
        value = read(lua.globals().Players[4], 4, 100001)
        self.assertEqual(to_python(value), {'unitID': 100001, 'unitType': 'UNIT_NATURALIST',
            'charges': 1, 'x': 8, 'y': 9, 'moves': 4, 'formation': 1})

    def test_zero_and_formation_snapshots_are_not_action_permission(self):
        lua, bridge = core_runtime()
        lua.globals().F.charges = 0
        lua.globals().F.moves = 0.0
        lua.globals().F.formation = 2
        value = lua.globals().BaiqiNaturalistUnit.Read(lua.globals().Players[4], 4, 100001)
        self.assertEqual((value.charges, value.moves, value.formation), (0, 0, 2))
        self.assertFalse(bridge.Prepare(4, 100001, 0, 8, 9)[0])

    def test_invalid_and_changing_native_data_fail_closed(self):
        for field, value in (('moves', float('nan')), ('charges', True),
                             ('formation', 0), ('throwCharges', True), ('changeOwnerDuringRead', True)):
            lua, _ = core_runtime()
            lua.globals().F[field] = value
            self.assertIsNone(lua.globals().BaiqiNaturalistUnit.Read(lua.globals().Players[4], 4, 100001))


class NaturalistJournalTests(unittest.TestCase):
    def setUp(self):
        self.lua = LuaRuntime(unpack_returned_tuples=True)
        self.journal = self.lua.execute((ROOT / 'mod/Baiqi/Lua/BaiqiNaturalistJournal.lua').read_text(encoding='utf-8'))

    def valid(self):
        return self.lua.execute("return {version=1,owner=4,serial=1,operations={['100001']={token='park:4:1',sequence=1,unitID=100001,unitType='UNIT_NATURALIST',charges=1,x=8,y=9,turn=56,stage='ARMED'}}}")

    def test_clone_is_independent_and_equal_checks_both_sides(self):
        value = self.valid()
        clone = self.journal.Clone(value, 4)
        self.assertTrue(self.journal.Equal(value, clone, 4))
        clone.operations['100001'].stage = 'OBSERVED'
        self.assertFalse(self.journal.Equal(value, clone, 4))
        self.assertEqual(value.operations['100001'].stage, 'ARMED')

    def test_unknown_keys_stages_tokens_and_duplicate_sequences_rejected(self):
        for expression in ("s.extra=true", "s.operations['100001'].stage='LEGACY_UNKNOWN'",
                           "s.operations['100001'].charges=0", "s.operations['100001'].token='park:4:2'",
                           "s.operations['100001'].unknown=true",
                           "s.operations.other=s.operations['100001']"):
            value = self.valid()
            self.lua.globals().s = value
            self.lua.execute(expression)
            self.assertFalse(self.journal.Validate(value, 4))
            self.assertIsNone(self.journal.Clone(value, 4))

    def test_limits_and_integer_contract(self):
        self.assertTrue(self.journal.Integer(0, 2147483647))
        self.assertFalse(self.journal.Integer(1, True))
        self.assertIsNone(self.journal.Token(4, 0))
        self.assertIsNone(self.journal.UnitKey(2147483648))
        state = self.lua.execute('''
          local s={version=1,owner=4,serial=257,operations={}}
          for i=1,257 do s.operations[tostring(i)]={token='park:4:'..i,sequence=i,unitID=i,
            unitType='UNIT_NATURALIST',charges=1,x=8,y=9,turn=56,stage='ARMED'} end
          return s
        ''')
        self.assertFalse(self.journal.Validate(state, 4))

    def test_metatables_and_unknown_owners_are_not_repaired(self):
        value = self.lua.execute("return setmetatable({}, {__index=function() error('metadata') end})")
        self.assertFalse(self.journal.Validate(value, 4))
        self.assertIsNone(self.journal.Clone(value, 4))
        self.assertFalse(self.journal.Equal(value, value, 4))
        self.assertFalse(self.journal.Validate(self.valid(), 3))


if __name__ == '__main__':
    unittest.main()
