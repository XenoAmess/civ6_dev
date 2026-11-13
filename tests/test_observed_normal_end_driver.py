"""Ordinary test-player END integration: reserve, gate, ACK, then actual activation."""
from pathlib import Path
import json
import unittest
import uuid

from tests.observed_driver_harness import DriverHarness
from tools.run_observed_acceptance import run


class NormalObservedDriverTests(unittest.TestCase):
    def setUp(self):
        self.h = DriverHarness()
        self.ledger = Path('.local-model/ordinary-observer-tests') / uuid.uuid4().hex
        self.calls = []

    def callback(self, turn, token):
        self.assertEqual(int(self.h.world.turn), turn)
        self.assertTrue(self.h.all_recording(True))
        stage = self.h.lua.globals().P6Q20StageB
        self.assertEqual(stage.token, token)
        self.assertTrue(stage.ends[turn])
        receipt = json.loads((self.ledger / f'end{turn}.json').read_text(encoding='utf-8'))
        self.assertEqual((receipt['turn'], receipt['token'], receipt['mode']), (turn, token, 'ORDINARY_CALLBACK'))
        self.assertFalse(self.h.world.diplomacy)
        self.calls.append((turn, token, float(self.h.world.clock)))
        # Model only the fixture's activation effect; never call its forced API.
        if self.h.advance:
            self.h.world.turn += 1
            target = int(self.h.world.turn)
            if self.h.activation_delay:
                self.h.pending.append((target, float(self.h.world.clock) + self.h.activation_delay))
            else:
                self.h._anchor(target)
        return {'turn': turn, 'token': token, 'requested': True, 'forced': False}

    def run_capture(self, callback=None, **kwargs):
        return run(self.h.query, self.h.diplomacy_visible, self.h.now, self.h.sleep,
                   self.h.emit, self.ledger, sample_budget=4096,
                   request_normal_end=self.callback if callback is None else callback, **kwargs)

    def test_complete_normal_capture_uses_one_token_and_no_forced_game_api(self):
        result = self.run_capture()
        self.assertEqual((result['phase'], result['turn']), ('COMPLETE', 91))
        self.assertEqual(result['requested_turns'], list(range(85, 91)))
        self.assertEqual([x[0] for x in self.calls], list(range(85, 91)))
        self.assertEqual({x[1] for x in self.calls}, {result['token']})
        self.assertEqual(self.h.actions, [])
        self.assertFalse(any('UserForced' in q or 'UI.RequestAction(' in q for q in self.h.queries))
        self.assertTrue(self.h.all_recording(False))

    def test_default_and_ambiguous_modes_fail_before_creating_capture(self):
        for options in ({}, {'legacy_forced': 1}, {'request_normal_end': False},
                        {'request_normal_end': self.callback, 'legacy_forced': True}):
            with self.subTest(options=options):
                self.setUp()
                with self.assertRaises((TypeError, ValueError)):
                    run(self.h.query, self.h.diplomacy_visible, self.h.now, self.h.sleep,
                        self.h.emit, self.ledger, **options)
                self.assertEqual((self.calls, self.h.actions, self.h.queries), ([], [], []))
                self.assertFalse(self.ledger.exists())

    def test_ack_without_actual_advance_times_out_and_does_not_repeat(self):
        self.h.advance = False
        with self.assertRaises(TimeoutError):
            self.run_capture()
        self.assertEqual([x[0] for x in self.calls], [85])
        self.assertEqual(int(self.h.world.turn), 85)
        self.assertTrue(self.h.all_recording(False))

    def test_throw_after_normal_effect_stops_without_replay(self):
        def uncertain(turn, token):
            self.callback(turn, token)
            raise OSError('ACK lost after ordinary effect')
        with self.assertRaises(OSError):
            self.run_capture(uncertain)
        self.assertEqual([x[0] for x in self.calls], [85])
        self.assertEqual(int(self.h.world.turn), 86)
        self.assertTrue(self.h.all_recording(False))

    def test_unknown_or_false_ack_after_effect_is_never_retried(self):
        values = [None, False, {}, {'turn': 85, 'token': 'wrong', 'requested': True, 'forced': False},
                  {'turn': True, 'token': None, 'requested': True, 'forced': False},
                  {'turn': 85, 'token': None, 'requested': False, 'forced': False},
                  {'turn': 85, 'token': None, 'requested': True, 'forced': True},
                  {'turn': 85, 'token': None, 'requested': True, 'forced': False, 'extra': 1}]
        for value in values:
            with self.subTest(value=value):
                self.setUp()
                def uncertain(turn, token):
                    self.callback(turn, token)
                    if type(value) is dict and value.get('token', 'missing') is None:
                        return dict(value, token=token)
                    return value
                with self.assertRaises(RuntimeError):
                    self.run_capture(uncertain)
                self.assertEqual([x[0] for x in self.calls], [85])
                self.assertTrue(self.h.all_recording(False))
                self.assertEqual(len(list(self.ledger.glob('end*.json'))), 1)

    def test_gate_failure_after_setup_prevents_callback_and_stops_recording(self):
        original = self.h.query
        def query(context, code):
            result = original(context, code)
            if 'P6_Q20_READY' in code:
                raise OSError('gate receipt lost, no END submitted')
            return result
        self.h.query = query
        with self.assertRaises(OSError):
            self.run_capture()
        self.assertEqual((self.calls, self.h.actions), ([], []))
        self.assertTrue(self.h.all_recording(False))

    def test_duplicate_gate_receipt_prevents_callback(self):
        original = self.h.query
        def query(context, code):
            result = original(context, code)
            if 'P6_Q20_READY' in code:
                row = next(x for x in result if x['tag'] == -1 and 'P6_Q20_READY' in x['payload'])
                return result + [dict(row)]
            return result
        self.h.query = query
        with self.assertRaises(RuntimeError):
            self.run_capture()
        self.assertEqual(self.calls, [])
        self.assertTrue(self.h.all_recording(False))

    def test_delayed_activation_and_diplomacy_wait_before_next_end(self):
        self.h.activation_delay = 2
        first_seen = []
        def visible(h):
            if h.world.turn == 87 and not first_seen:
                first_seen.append(float(h.world.clock))
            return h.world.turn == 87 and h.world.clock < first_seen[0] + 3
        self.h.visibility = visible
        self.run_capture()
        for turn, _, at in self.calls[1:]:
            self.assertGreaterEqual(at, self.h.anchor_times[turn] + 10)
        self.assertEqual(self.h.actions, [])

    def test_existing_ledger_and_bad_global_quota_submit_no_end(self):
        self.ledger.mkdir(parents=True)
        (self.ledger / 'end85.json').write_text('{}', encoding='utf-8')
        with self.assertRaises(FileExistsError):
            self.run_capture()
        self.assertEqual((self.calls, self.h.queries), ([], []))
        self.setUp()
        self.h.lua.execute('for _,e in pairs(ExposedMembers.P6BaiqiOwnRegistry.entries)do e.Snapshot().profile.capacity=129 end')
        with self.assertRaises(Exception):
            self.run_capture()
        self.assertEqual((self.calls, self.h.actions), ([], []))
        self.assertTrue(self.h.all_recording(False))

    def test_post_ack_visit_is_reported_without_repeating_callback(self):
        self.h.advance = False
        self.h.visibility = lambda h: bool(self.calls)
        with self.assertRaises(TimeoutError):
            self.run_capture()
        self.assertEqual([x[0] for x in self.calls], [85])
        self.assertIn('TEST_PLAYER_DIPLOMACY_ACTIVE turn=85', self.h.logs)
        self.assertEqual(self.h.logs.count('TEST_PLAYER_DIPLOMACY_ACTIVE turn=85'), 1)
        self.assertTrue(self.h.all_recording(False))

    def test_visit_before_ten_seconds_is_reported_before_end_gate(self):
        seen = []
        def visible(h):
            if h.world.turn == 86 and not seen:
                seen.append(float(h.world.clock))
            return h.world.turn == 86 and h.world.clock < seen[0] + 3
        self.h.visibility = visible
        result = self.run_capture()
        self.assertEqual(result['phase'], 'COMPLETE')
        self.assertLess(seen[0], self.h.anchor_times[86] + 10)
        self.assertIn('TEST_PLAYER_DIPLOMACY_ACTIVE turn=86', self.h.logs)
        self.assertEqual([x[0] for x in self.calls], list(range(85, 91)))


if __name__ == '__main__':
    unittest.main()
