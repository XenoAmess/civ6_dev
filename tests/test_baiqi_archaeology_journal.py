import copy
import json
import unittest
from archaeology_journal_harness import ROOT, load_archaeology_journal, excavation_state, to_lua


class ArchaeologyJournalTests(unittest.TestCase):
    def setUp(self):
        self.lua, self.j = load_archaeology_journal()

    def valid(self, value):
        return self.j.Validate(to_lua(self.lua, value), 7)

    def phase(self, stage='OBSERVED', unit=4, sequence=1, work=101):
        state = excavation_state()
        op = state['operations'].pop('4')
        state['serial'] = sequence
        op.update(unitID=unit, sequence=sequence, token=f'archaeology:7:{sequence}')
        if stage != 'EXCAVATE_ARMED':
            op.update(stage=stage, artifactIndex=5, artifactType=0, actingPlayerID=7,
                      choicePlayerID=7, choiceTurn=92, targetPlayerID=8)
        if stage == 'OBSERVED':
            op.update(newWorkID=work, works={str(work): True})
        state['operations'][str(unit)] = op
        return state

    def test_eight_reviewed_contract_data_cases(self):
        cases = json.loads((ROOT / 'tests/fixtures/archaeology_journal_cases.json').read_text(encoding='utf-8'))
        self.assertEqual(len(cases), 8)
        for case in cases:
            with self.subTest(case=case['name']):
                self.assertEqual(self.valid(case['state']), case['valid'])

    def test_new_keys_tokens_and_numeric_bounds(self):
        self.assertTrue(self.j.Validate(self.j.New(7), 7))
        self.assertEqual((self.j.UnitKey(0), self.j.UnitKey(-0.0), self.j.Token(7, 1)), ('0', '0', 'archaeology:7:1'))
        self.assertTrue(self.j.Integer(2147483647, 2147483647))
        for value in (True, -1, 0.5, float('inf'), float('nan'), 2147483648):
            with self.subTest(value=value):
                self.assertFalse(self.j.Integer(value, 2147483647))
                self.assertIsNone(self.j.UnitKey(value))
        self.assertIsNone(self.j.Token(7, 0))
        self.assertIsNone(self.j.New(True))

    def test_all_three_positive_stages_and_zero_work_id(self):
        for stage in ('EXCAVATE_ARMED', 'CHOICE_ARMED', 'OBSERVED'):
            with self.subTest(stage=stage):
                self.assertTrue(self.valid(self.phase(stage)))
        self.assertTrue(self.valid(self.phase(work=0)))

    def test_clone_and_equality_are_deep_and_symmetric(self):
        original = to_lua(self.lua, self.phase())
        cloned = self.j.Clone(original, 7)
        self.assertTrue(self.j.Equal(original, cloned, 7))
        cloned.operations['4'].works['102'] = True
        self.assertIsNone(original.operations['4'].works['102'])
        self.assertFalse(self.j.Equal(original, cloned, 7))
        self.assertFalse(self.j.Equal(cloned, original, 7))
        cloned.operations['4'].works['102'] = None
        cloned.operations['4'].baselineWorkIDs[1] = 50
        self.assertIsNone(original.operations['4'].baselineWorkIDs[1])
        self.assertFalse(self.j.Equal(original, cloned, 7))

    def test_sequences_are_unique_across_distinct_full_unit_keys(self):
        value = self.phase()
        second = self.phase(unit=5, sequence=1, work=102)
        value['operations'].update(second['operations'])
        self.assertFalse(self.valid(value))
        value['serial'] = 2
        value['operations']['5'].update(sequence=2, token='archaeology:7:2')
        self.assertTrue(self.valid(value))

    def test_global_work_uniqueness_and_one_unresolved_operation(self):
        value = self.phase()
        value['serial'] = 2
        value['operations'].update(self.phase(unit=5, sequence=2)['operations'])
        self.assertFalse(self.valid(value))
        value['operations']['5'].update(newWorkID=102, works={'102': True})
        self.assertTrue(self.valid(value))
        value['operations']['5'] = self.phase('CHOICE_ARMED', 5, 2)['operations']['5']
        self.assertTrue(self.valid(value))
        value['operations']['4'] = self.phase('EXCAVATE_ARMED')['operations']['4']
        self.assertFalse(self.valid(value))

    def test_dense_sorted_baseline_is_independent_of_lua_array_partition(self):
        for baseline in ({1: 1, 3: 2}, {2: 1}, {0: 1}, {'1': 1}, {True: 1}):
            with self.subTest(baseline=baseline):
                value = excavation_state()
                value['operations']['4']['baselineWorkIDs'] = baseline
                self.assertFalse(self.valid(value))
        for baseline in ([2, 1], [1, 1], [True], [-1]):
            with self.subTest(baseline=baseline):
                value = excavation_state()
                value['operations']['4']['baselineWorkIDs'] = baseline
                self.assertFalse(self.valid(value))

    def test_canonical_work_map_requires_string_keys_and_exact_true(self):
        for works in ({101: True}, {'0101': True}, {'101.0': True}, {'+101': True},
                      {'-1': True}, {'101': 1}, {'101': False}):
            with self.subTest(works=works):
                value = excavation_state()
                value['operations']['4']['works'] = works
                self.assertFalse(self.valid(value))

    def test_phase_fields_target_policy_and_observed_new_work_proof(self):
        for kind in range(6):
            value = self.phase('CHOICE_ARMED')
            op = value['operations']['4']
            op['artifactType'] = kind
            if kind in (1, 2, 5):
                op.pop('targetPlayerID')
            self.assertTrue(self.valid(value))
            op['choicePlayerID'] = 8
            self.assertFalse(self.valid(value))
        for mutation in ({'newWorkID': 100}, {'baselineWorkIDs': [101]},
                         {'works': {}}, {'choiceTurn': 91}):
            value = self.phase()
            value['operations']['4'].update(mutation)
            self.assertFalse(self.valid(value))
        value = excavation_state()
        value['operations']['4']['artifactIndex'] = 5
        self.assertFalse(self.valid(value))

    def test_capacity_limits_for_operations_history_and_baseline(self):
        value = {'version': 1, 'owner': 7, 'serial': 256, 'operations': {}}
        for i in range(1, 257):
            value['operations'].update(self.phase(unit=i, sequence=i, work=i)['operations'])
        self.assertTrue(self.valid(value))
        value['serial'] = 257
        value['operations'].update(self.phase(unit=257, sequence=257, work=257)['operations'])
        self.assertFalse(self.valid(value))
        value = excavation_state()
        op = value['operations']['4']
        op.update(works={str(i): True for i in range(64)}, baselineWorkIDs=list(range(64)))
        self.assertTrue(self.valid(value))
        op['works']['64'] = True
        self.assertFalse(self.valid(value))
        op['works'].pop('64')
        op['baselineWorkIDs'].append(64)
        self.assertFalse(self.valid(value))

    def test_unknown_fields_identity_resource_and_serial_are_rejected(self):
        for field, val in (('unknown', 0), ('unitType', 'UNIT_NATURALIST'),
                           ('resourceType', 'RESOURCE_IRON'), ('sequence', 2),
                           ('homeCityID', True), ('x', float('nan'))):
            value = excavation_state()
            value['operations']['4'][field] = val
            self.assertFalse(self.valid(value))
        value = excavation_state()
        value['unknown'] = 0
        self.assertFalse(self.valid(value))
        value = excavation_state()
        value['operations']['04'] = value['operations'].pop('4')
        self.assertFalse(self.valid(value))

    def test_metatables_and_cycles_fail_without_escape(self):
        value = to_lua(self.lua, excavation_state())
        self.lua.eval('function(s) setmetatable(s.operations["4"].works,{}) end')(value)
        self.assertFalse(self.j.Validate(value, 7))
        self.assertIsNone(self.j.Clone(value, 7))
        value = to_lua(self.lua, excavation_state())
        value.operations['4'].baselineWorkIDs[1] = value
        self.assertFalse(self.j.Validate(value, 7))


if __name__ == '__main__':
    unittest.main()
