import copy
import unittest
from tools.modal_readiness_evidence import classify_modal_readiness


class ModalReadinessTests(unittest.TestCase):
    def setUp(self):
        self.ui = dict(scope_key='owned', local_player=0, turn=291, active=True,
                       allowed=True, busy=False, messages=False, can_end_turn=False)
        self.scene = dict(scope_key='owned', local_player=0, turn=291, hidden=True)
        self.modals = [dict(context=n, scope_key='owned', local_player=0, turn=291, hidden=True)
                       for n in ('WorldCongressPopup', 'WorldCongressBetweenTurns', 'WorldCongressIntro')]

    def result(self):
        return classify_modal_readiness(291, self.ui, self.scene, self.modals)

    def test_hidden_complete_set_preserves_ready_and_wait(self):
        self.assertEqual(self.result()['status'], 'READY')
        self.ui['allowed'] = False
        self.assertEqual(self.result()['status'], 'WAIT_AI')

    def test_every_visible_context_blocks_ready_and_wait(self):
        for index in range(3):
            for allowed in (True, False):
                with self.subTest(index=index, allowed=allowed):
                    self.setUp(); self.ui['allowed'] = allowed
                    self.modals[index]['hidden'] = False
                    self.assertEqual(self.result()['status'], 'MODAL_BLOCKED')
                    self.assertFalse(self.result()['qualified'])

    def test_malformed_base_never_throws_or_grants_ready(self):
        for value in (None, {}, [], 'bad', False):
            self.assertEqual(classify_modal_readiness(291, value, self.scene, self.modals)['status'], 'UNKNOWN')
            self.assertEqual(classify_modal_readiness(291, self.ui, value, self.modals)['status'], 'UNKNOWN')

    def test_complete_collection_required(self):
        for modals in (None, {}, [], self.modals[:2], self.modals + [self.modals[0]],
                       [self.modals[0], self.modals[0], self.modals[2]]):
            self.assertEqual(classify_modal_readiness(291, self.ui, self.scene, modals)['status'], 'UNKNOWN')

    def test_all_fields_of_every_modal_required(self):
        for index in range(3):
            for field in self.modals[index]:
                modals = copy.deepcopy(self.modals); del modals[index][field]
                with self.subTest(index=index, field=field):
                    self.assertEqual(classify_modal_readiness(291, self.ui, self.scene, modals)['status'], 'UNKNOWN')

    def test_invalid_fields_remain_unknown(self):
        for field, values in {
            'context': (None, [], 'Other', 'LeaderScene'),
            'scope_key': (None, '', 0), 'local_player': (True, 0.0, 1, None),
            'turn': (True, 291.0, -1, None, float('inf'), float('nan'), 10 ** 10000),
            'hidden': (0, 1, None, 'false')}.items():
            for value in values:
                modals = copy.deepcopy(self.modals); modals[2][field] = value
                result = classify_modal_readiness(291, self.ui, self.scene, modals)
                self.assertEqual(result['status'], 'UNKNOWN', field)

    def test_no_visible_prefix_qualification(self):
        self.modals[0]['hidden'] = False
        self.modals[2]['hidden'] = 'unknown'
        self.assertEqual(self.result()['status'], 'UNKNOWN')

    def test_scope_and_actual_turn_alignment_required(self):
        for field, value in [('scope_key', 'other'), ('turn', 290)]:
            modals = copy.deepcopy(self.modals); modals[1][field] = value
            self.assertEqual(classify_modal_readiness(291, self.ui, self.scene, modals)['status'], 'UNKNOWN')

    def test_unknown_passed_and_npc_have_priority_when_all_valid(self):
        self.modals[0]['hidden'] = False
        self.scene['hidden'] = False
        self.assertEqual(self.result()['status'], 'NPC_BLOCKED')
        self.ui['turn'] = self.scene['turn'] = 292
        for m in self.modals: m['turn'] = 292
        self.assertEqual(self.result()['status'], 'TURN_PASSED')
        self.ui['turn'] = self.scene['turn'] = 289
        for m in self.modals: m['turn'] = 289
        self.assertEqual(self.result()['status'], 'UNKNOWN')

    def test_input_unchanged_and_extras_not_returned(self):
        self.modals[0]['private_extra'] = {'data': [1, 2]}
        before = copy.deepcopy((self.ui, self.scene, self.modals))
        result = self.result()
        self.assertEqual((self.ui, self.scene, self.modals), before)
        self.assertEqual(set(result), {'status', 'qualified', 'reason'})


if __name__ == '__main__': unittest.main()
