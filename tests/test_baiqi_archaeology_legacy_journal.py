import copy
import unittest
from archaeology_journal_harness import load_archaeology_journal, excavation_state, to_lua


def pending_state(observed=False):
    value = excavation_state()
    op = value['operations']['4']
    op.pop('resourceIndex')
    op.pop('resourceType')
    op.update(legacy=True, stage='CHOICE_ARMED', artifactIndex=5, artifactType=3,
              actingPlayerID=2, choicePlayerID=2, targetPlayerID=3, choiceTurn=92)
    if observed:
        op.update(stage='OBSERVED', newWorkID=101, works={'101': True})
    return value


class ArchaeologyLegacyJournalTests(unittest.TestCase):
    def setUp(self):
        self.lua, self.j = load_archaeology_journal()

    def valid(self, value):
        return self.j.Validate(to_lua(self.lua, value), 7)

    def test_actual_pending_choice_and_observed_schema_need_no_fabricated_resource(self):
        for observed in (False, True):
            with self.subTest(observed=observed):
                self.assertTrue(self.valid(pending_state(observed)))

    def test_normal_resource_contract_still_required(self):
        value = excavation_state()
        self.assertTrue(self.valid(value))
        for field in ('resourceIndex', 'resourceType'):
            changed = copy.deepcopy(value)
            changed['operations']['4'].pop(field)
            self.assertFalse(self.valid(changed))

    def test_legacy_never_authorizes_excavation_or_historical_resource_claim(self):
        for mutation in ({'stage': 'EXCAVATE_ARMED'}, {'resourceIndex': 9},
                         {'resourceType': 'RESOURCE_ANTIQUITY_SITE'}, {'choiceTurn': 93}):
            value = pending_state()
            value['operations']['4'].update(mutation)
            self.assertFalse(self.valid(value))

    def test_optional_flag_is_only_exact_true_or_absent(self):
        for flag in (False, 0, 1, 'true', {}):
            value = pending_state()
            value['operations']['4']['legacy'] = flag
            self.assertFalse(self.valid(value))
        value = pending_state()
        value['operations']['4'].pop('legacy')
        self.assertFalse(self.valid(value))

    def test_legacy_clone_is_deep_and_equality_distinguishes_origin(self):
        a = to_lua(self.lua, pending_state(True))
        b = self.j.Clone(a, 7)
        self.assertTrue(self.j.Equal(a, b, 7))
        b.operations['4'].works['102'] = True
        self.assertIsNone(a.operations['4'].works['102'])
        self.assertFalse(self.j.Equal(a, b, 7))
        normal = pending_state(True)
        normal['operations']['4'].pop('legacy')
        normal['operations']['4'].update(resourceIndex=9, resourceType='RESOURCE_ANTIQUITY_SITE')
        c = to_lua(self.lua, normal)
        self.assertTrue(self.j.Validate(c, 7))
        self.assertFalse(self.j.Equal(a, c, 7))
        self.assertFalse(self.j.Equal(c, a, 7))

    def test_existing_descriptor_work_uniqueness_and_one_unresolved_rules_apply(self):
        for mutation in ({'choicePlayerID': 3}, {'targetPlayerID': -1}, {'baselineWorkIDs': [101]},
                         {'works': {101: True}}, {'newWorkID': 102}):
            value = pending_state(True)
            value['operations']['4'].update(mutation)
            self.assertFalse(self.valid(value))
        value = pending_state()
        value['serial'] = 2
        other = copy.deepcopy(value['operations']['4'])
        other.update(unitID=5, sequence=2, token='archaeology:7:2')
        value['operations']['5'] = other
        self.assertFalse(self.valid(value))


if __name__ == '__main__':
    unittest.main()
