"""Readiness evidence must not turn stale, foreign or malformed observations into READY."""
import copy
import unittest

from tools.readiness_evidence import classify_readiness


class ReadinessEvidenceTests(unittest.TestCase):
    def setUp(self):
        self.ui = dict(scope_key='pid-birth-seeds', local_player=0, turn=290,
                       active=True, allowed=True, busy=False, messages=False,
                       can_end_turn=False)
        self.scene = dict(scope_key='pid-birth-seeds', local_player=0, turn=290, hidden=True)

    def classify(self, expected=290):
        return classify_readiness(expected, self.ui, self.scene)

    def test_ready_does_not_require_or_grant_end_permission(self):
        result = self.classify()
        self.assertEqual(result['status'], 'READY')
        self.assertTrue(result['qualified'])
        self.assertEqual(set(result), {'status', 'qualified', 'reason'})

    def test_each_busy_or_inactive_condition_waits(self):
        for field, value in [('active', False), ('allowed', False),
                             ('busy', True), ('messages', True)]:
            with self.subTest(field=field):
                ui = dict(self.ui, **{field: value})
                result = classify_readiness(290, ui, self.scene)
                self.assertEqual(result['status'], 'WAIT_AI')
                self.assertFalse(result['qualified'])

    def test_previous_turn_waits_even_when_flags_look_ready(self):
        self.ui['turn'] = self.scene['turn'] = 289
        self.assertEqual(self.classify()['status'], 'WAIT_AI')

    def test_visible_scene_is_npc_blocked(self):
        for turn in (289, 290):
            self.ui['turn'] = self.scene['turn'] = turn
            self.scene['hidden'] = False
            self.assertEqual(self.classify()['status'], 'NPC_BLOCKED')
            self.assertFalse(self.classify()['qualified'])

    def test_passed_and_old_turns_cannot_become_ready(self):
        for turn, status in [(291, 'TURN_PASSED'), (288, 'UNKNOWN')]:
            self.ui['turn'] = self.scene['turn'] = turn
            self.scene['hidden'] = False
            self.assertEqual(self.classify()['status'], status)
            self.assertFalse(self.classify()['qualified'])

    def test_alignment_precedes_npc_and_ready(self):
        for field, value in [('scope_key', 'other-instance'), ('turn', 289),
                             ('local_player', 1)]:
            with self.subTest(field=field):
                scene = dict(self.scene, hidden=False, **{field: value})
                self.assertEqual(classify_readiness(290, self.ui, scene)['status'], 'UNKNOWN')

    def test_missing_every_required_field_is_unknown(self):
        for side, original in [('ui', self.ui), ('scene', self.scene)]:
            for field in original:
                with self.subTest(side=side, field=field):
                    bad = dict(original)
                    del bad[field]
                    result = classify_readiness(290, bad if side == 'ui' else self.ui,
                                                bad if side == 'scene' else self.scene)
                    self.assertEqual(result['status'], 'UNKNOWN')

    def test_boolean_and_numeric_types_remain_strict(self):
        for side, original in [('ui', self.ui), ('scene', self.scene)]:
            fields = ['local_player', 'turn']
            fields += ['active', 'allowed', 'busy', 'messages', 'can_end_turn'] if side == 'ui' else ['hidden']
            for field in fields:
                invalids = (True, 0.0, None, '0') if field in ('local_player', 'turn') else (0, 1, None, 'false')
                for value in invalids:
                    with self.subTest(side=side, field=field, value=value):
                        bad = dict(original, **{field: value})
                        result = classify_readiness(290, bad if side == 'ui' else self.ui,
                                                   bad if side == 'scene' else self.scene)
                        self.assertEqual(result['status'], 'UNKNOWN')

    def test_huge_integer_is_unknown_in_all_three_positions(self):
        huge = 10 ** 10000
        for expected, ui, scene in [(huge, self.ui, self.scene),
                                   (290, dict(self.ui, turn=huge), self.scene),
                                   (290, self.ui, dict(self.scene, turn=huge))]:
            self.assertEqual(classify_readiness(expected, ui, scene)['status'], 'UNKNOWN')

    def test_bad_expected_and_observation_containers_are_unknown(self):
        for expected in (None, True, -1, 100001, 290.0, float('nan'), float('inf'), [], {}):
            self.assertEqual(self.classify(expected)['status'], 'UNKNOWN')
        for value in (None, [], 'ui', 0, False):
            self.assertEqual(classify_readiness(290, value, self.scene)['status'], 'UNKNOWN')
            self.assertEqual(classify_readiness(290, self.ui, value)['status'], 'UNKNOWN')
        for scope in ('', None, 0):
            self.assertEqual(classify_readiness(290, dict(self.ui, scope_key=scope), self.scene)['status'], 'UNKNOWN')

    def test_input_unchanged_and_extra_fields_not_exposed(self):
        self.ui['private_extra'] = {'secret': [1, 2]}
        before = copy.deepcopy((self.ui, self.scene))
        result = self.classify()
        self.assertEqual((self.ui, self.scene), before)
        self.assertNotIn('private_extra', result)


if __name__ == '__main__':
    unittest.main()
