import unittest
from archaeology_intent_harness import ROOT, KEY, archaeology_runtime
from archaeology_journal_harness import excavation_state, to_lua


class ArchaeologyIntentTests(unittest.TestCase):
    def setUp(self):
        self.lua, self.module, self.h = archaeology_runtime()
        self.b = self.module.bridge

    def arm(self):
        result = self.b.PrepareExcavation(7, 4, self.h.proposal)
        self.assertEqual(result[:2], (True, 'archaeology:7:1'))
        return result[1]

    def choose(self):
        token = self.arm()
        result = self.b.PrepareChoice(7, 4, token, self.h.descriptor)
        self.assertEqual(result[:2], (True, token))
        return token

    def op(self):
        return self.h.store[KEY].operations['4']

    def test_actual_export_and_empty_inspection_have_no_write(self):
        self.assertTrue(self.lua.eval('ExposedMembers.BaiqiArchaeologyBridge==BaiqiArchaeologyIntentGameplay.bridge'))
        self.assertEqual(self.b.Inspect(7, 4)[:2], ('OPEN', None))
        self.assertEqual(self.h.writes, 0)

    def test_excavation_permission_is_persisted_before_grant(self):
        self.arm()
        self.assertEqual((self.op().stage, self.h.store[KEY].serial, self.h.writes), ('EXCAVATE_ARMED', 1, 1))
        self.assertTrue(self.lua.globals().BaiqiArchaeologyJournal.Validate(self.h.store[KEY], 7))
        self.assertEqual(self.b.Inspect(7, 4)[:2], ('EXCAVATE_ARMED', 'archaeology:7:1'))

    def test_any_unresolved_permission_holds_all_new_excavations(self):
        self.arm()
        self.assertFalse(self.b.PrepareExcavation(7, 4, self.h.proposal)[0])
        self.h.unitID = 5
        self.assertFalse(self.b.PrepareExcavation(7, 5, self.h.proposal)[0])
        self.assertEqual(self.b.Inspect(7, 5)[0], 'BUSY')
        self.assertEqual(self.h.writes, 1)

    def test_choice_accepts_original_or_removed_resource_and_zero_moves(self):
        for index in (9, -1):
            with self.subTest(resource=index):
                self.setUp()
                token = self.arm()
                self.h.resourceIndex = index
                self.h.moves = 0
                self.assertEqual(self.b.PrepareChoice(7, 4, token, self.h.descriptor)[:2], (True, token))
                self.assertEqual((self.op().stage, self.op().choiceTurn, self.h.store[KEY].serial), ('CHOICE_ARMED', 92, 1))

    def test_other_resource_never_becomes_removed_resource_proof(self):
        token = self.arm()
        self.h.resourceIndex = 10
        self.assertFalse(self.b.PrepareChoice(7, 4, token, self.h.descriptor)[0])
        self.assertEqual((self.op().stage, self.h.writes), ('EXCAVATE_ARMED', 1))

    def test_choice_rechecks_fresh_owner_formation_visibility_and_turn(self):
        for field, value in (('formation',2), ('cityOwner',8), ('siteOwner',8),
                             ('visible',False), ('turn',93)):
            with self.subTest(field=field):
                self.setUp()
                token = self.arm()
                self.h.mutateField = field
                self.h.mutateValue = value
                self.lua.execute('H.onResource=function(n) if n==3 then H[H.mutateField]=H.mutateValue end end')
                self.assertFalse(self.b.PrepareChoice(7, 4, token, self.h.descriptor)[0])
                self.assertEqual((self.op().stage, self.h.writes), ('EXCAVATE_ARMED', 1))

    def test_created_fact_settles_consumed_unit_and_replay_does_not_write(self):
        self.choose()
        self.h.unitExists = False
        self.h.active = False
        self.assertTrue(self.module.ObserveCreated(7, 4, 2, 3, 24, 101))
        self.assertEqual((self.op().stage, self.op().newWorkID, self.op().works['101'], self.h.writes), ('OBSERVED', 101, True, 3))
        self.assertEqual(self.b.Inspect(7, 4)[0], 'OBSERVED')
        self.assertFalse(self.module.ObserveCreated(7, 4, 2, 3, 24, 101))
        self.assertEqual(self.h.writes, 3)

    def test_foreign_or_wrong_created_payload_never_confirms(self):
        self.choose()
        for payload in ((8,4,2,3,24,101), (7,5,2,3,24,101), (7,4,4,3,24,101),
                        (7,4,2,3,23,101), (7,4,2,3,24,-1)):
            self.assertFalse(self.module.ObserveCreated(*payload), payload)
        self.assertEqual((self.op().stage, self.h.writes), ('CHOICE_ARMED', 2))

    def test_baseline_work_is_not_new_receipt(self):
        self.h.proposal.baselineWorkIDs = self.lua.table_from([101])
        self.choose()
        self.assertFalse(self.module.ObserveCreated(7, 4, 2, 3, 24, 101))
        self.assertTrue(self.module.ObserveCreated(7, 4, 2, 3, 24, 102))

    def test_resource_boundary_changes_are_rechecked_before_persist(self):
        for field, value in (('moves',0), ('formation',2), ('cityOwner',8),
                             ('siteOwner',8), ('visible',False), ('turn',93)):
            with self.subTest(field=field):
                self.setUp()
                self.h.mutateField = field
                self.h.mutateValue = value
                self.lua.execute('H.onResource=function(n) if n==1 then H[H.mutateField]=H.mutateValue end end')
                self.assertFalse(self.b.PrepareExcavation(7, 4, self.h.proposal)[0])
                self.assertEqual(self.h.writes, 0)

    def test_missing_owner_position_and_visibility_methods_fail_closed(self):
        for expression in ('H.city.GetOwner=nil', 'H.city.GetID=nil', 'H.plot.GetOwner=nil',
                           'H.plot.GetX=nil', 'H.visibility.IsVisible=nil', 'H.visibility.IsRevealed=nil'):
            with self.subTest(expression=expression):
                self.setUp()
                self.lua.execute(expression)
                self.assertFalse(self.b.PrepareExcavation(7, 4, self.h.proposal)[0])
                self.assertEqual(self.h.writes, 0)

    def test_unreadable_corrupt_or_unconfirmed_write_never_grants(self):
        self.h.throwRead = True
        self.assertFalse(self.b.PrepareExcavation(7, 4, self.h.proposal)[0])
        self.h.throwRead = False
        self.h.store[KEY] = self.lua.table_from({'unknown': True})
        self.assertEqual(self.b.Inspect(7, 4)[0], 'UNAVAILABLE')
        self.assertFalse(self.b.PrepareExcavation(7, 4, self.h.proposal)[0])
        self.assertEqual(self.h.writes, 0)
        self.h.store[KEY] = None
        self.h.allowWrite = False
        self.assertFalse(self.b.PrepareExcavation(7, 4, self.h.proposal)[0])
        self.assertIsNone(self.h.store[KEY])

    def test_write_then_throw_remains_armed_and_never_regrants(self):
        self.h.writeThenThrow = True
        self.assertFalse(self.b.PrepareExcavation(7, 4, self.h.proposal)[0])
        self.h.writeThenThrow = False
        self.assertEqual(self.b.Inspect(7, 4)[0], 'EXCAVATE_ARMED')
        self.assertFalse(self.b.PrepareExcavation(7, 4, self.h.proposal)[0])
        self.assertEqual(self.h.writes, 1)

    def test_changed_property_is_not_overwritten_by_new_proposal(self):
        self.lua.execute('H.onResource=function(n) if n==1 then local s=BaiqiArchaeologyJournal.New(7);s.serial=5;H.store["BAIQI_ARCHAEOLOGY_INTENTS_V1"]=s end end')
        self.assertFalse(self.b.PrepareExcavation(7, 4, self.h.proposal)[0])
        self.assertEqual((self.h.store[KEY].serial, self.h.writes), (5, 0))

    def test_owner_and_missing_config_gate_without_property_write(self):
        for field, val in (('leader','LEADER_GORGO'), ('localPlayer',8), ('human',False),
                           ('active',False), ('multi',True), ('hotseat',True)):
            with self.subTest(field=field):
                self.setUp()
                self.h[field] = val
                self.assertFalse(self.b.PrepareExcavation(7, 4, self.h.proposal)[0])
                self.assertEqual(self.h.writes, 0)
        lua, module, h = archaeology_runtime(inject_key=False)
        self.assertFalse(module.bridge.PrepareExcavation(7, 4, h.proposal)[0])
        self.assertEqual((h.reads, h.writes), (0, 0))

    def test_proposals_and_descriptors_are_exact_plain_packets(self):
        self.h.proposal.unexpected = 1
        self.assertFalse(self.b.PrepareExcavation(7, 4, self.h.proposal)[0])
        self.h.proposal.unexpected = None
        self.lua.execute('setmetatable(H.proposal,{})')
        self.assertFalse(self.b.PrepareExcavation(7, 4, self.h.proposal)[0])
        self.lua.execute('setmetatable(H.proposal,nil)')
        token = self.arm()
        self.h.descriptor.choicePlayerID = 3
        self.assertFalse(self.b.PrepareChoice(7, 4, token, self.h.descriptor)[0])
        self.h.descriptor.choicePlayerID = 2
        self.assertFalse(self.b.PrepareChoice(7, 4, 'archaeology:7:999', self.h.descriptor)[0])

    def test_foreign_modules_bridges_and_malformed_namespace_survive(self):
        lua, module, h = archaeology_runtime(before_module="BaiqiArchaeologyIntentGameplay={marker='foreign',version=9}")
        self.assertEqual(module.marker, 'foreign')
        self.assertEqual(h.writes, 0)
        lua, module, h = archaeology_runtime(before_module="ExposedMembers.BaiqiArchaeologyBridge={marker='foreign'}")
        self.assertEqual(lua.globals().ExposedMembers.BaiqiArchaeologyBridge.marker, 'foreign')
        lua, module, h = archaeology_runtime(before_module="ExposedMembers=setmetatable({},{__index=function() error('namespace') end})")
        self.assertIsNotNone(module.bridge)
        self.assertEqual(h.writes, 0)

    def test_full_operation_capacity_allows_reuse_but_not_new_unit_or_full_history(self):
        state = {'version': 1, 'owner': 7, 'serial': 256, 'operations': {}}
        for unit_id in range(1, 257):
            op = excavation_state()['operations']['4']
            op.update(unitID=unit_id, sequence=unit_id, token=f'archaeology:7:{unit_id}',
                      stage='OBSERVED', artifactIndex=5, artifactType=0,
                      actingPlayerID=2, choicePlayerID=2, choiceTurn=92, targetPlayerID=3,
                      newWorkID=1000+unit_id, works={str(1000+unit_id): True})
            state['operations'][str(unit_id)] = op
        self.h.store[KEY] = to_lua(self.lua, state)
        self.h.unitID = 999
        self.assertFalse(self.b.PrepareExcavation(7, 999, self.h.proposal)[0])
        self.assertEqual(self.h.writes, 0)
        self.h.unitID = 4
        result = self.b.PrepareExcavation(7, 4, self.h.proposal)
        self.assertEqual(result[:2], (True, 'archaeology:7:257'))
        self.assertEqual((self.op().works['1004'], self.h.store[KEY].serial), (True, 257))
        state['operations']['4'].update(newWorkID=2000, works={str(i): True for i in range(2000, 2064)})
        self.h.store[KEY] = to_lua(self.lua, state)
        self.assertFalse(self.b.PrepareExcavation(7, 4, self.h.proposal)[0])
        self.assertEqual(self.h.writes, 1)


if __name__ == '__main__':
    unittest.main()
