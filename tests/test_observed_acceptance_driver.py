import unittest
from pathlib import Path
import uuid
from observed_driver_harness import DriverHarness
from tools.run_observed_acceptance import run

ROOT = Path(__file__).resolve().parents[1]

class TestObservedAcceptance(unittest.TestCase):
    def setUp(self):
        self.h = DriverHarness()
        self.ledger = ROOT / '.local-model/observed-driver-tests' / uuid.uuid4().hex

    def _run(self, **kwargs):
        return run(self.h.query, self.h.diplomacy_visible, self.h.now, self.h.sleep, self.h.emit, self.ledger, **kwargs)

    def test_complete_window(self):
        res = self._run()
        self.assertEqual(res['phase'], 'COMPLETE')
        self.assertEqual(res['turn'], 91)
        self.assertEqual(res['requested_turns'], [85, 86, 87, 88, 89, 90])
        self.assertEqual(len(list(self.ledger.glob('end*.json'))), 6)
        self.assertEqual(self.h.actions, [85, 86, 87, 88, 89, 90])
        self.assertEqual([(value,turn) for _,value,turn in self.h.recordings], [(True,85)]*32+[(False,91)]*32)
        self.assertTrue(self.h.all_recording(False))

    def test_visible_diplomacy_blocks_end(self):
        first_seen = None
        def vis(h):
            nonlocal first_seen
            if h.world.turn == 87 and first_seen is None:
                first_seen = h.world.clock
            return h.world.turn == 87 and h.world.clock < first_seen + 3
        self.h.visibility = vis
        res = self._run()
        self.assertEqual(res['phase'], 'COMPLETE')
        self.assertEqual(res['requested_turns'], [85,86,87,88,89,90])
        self.assertGreaterEqual(dict(self.h.action_times)[87], first_seen+3)
        self.assertIn('TEST_PLAYER_DIPLOMACY_ACTIVE turn=87', self.h.logs)

    def test_delayed_anchor_waits(self):
        self.h.activation_delay = 2
        res = self._run()
        self.assertEqual(res['phase'], 'COMPLETE')
        self.assertEqual(res['requested_turns'], [85, 86, 87, 88, 89, 90])

        for turn,at in self.h.action_times:
            if turn>=86:self.assertGreaterEqual(at, self.h.anchor_times[turn]+10)

    def test_readonly_poll_retry(self):
        self.h.fail_poll_once = True
        res = self._run()
        self.assertEqual(res['phase'], 'COMPLETE')
        self.assertIn('READONLY_POLL_TRANSPORT OSError', self.h.logs)
        self.assertEqual(res['requested_turns'], [85, 86, 87, 88, 89, 90])

    def test_unknown_ack_abort(self):
        self.h.raise_after_action_turn = 86
        with self.assertRaises(OSError):
            self._run()
        self.assertEqual(self.h.actions, [85, 86])
        self.assertTrue(self.h.all_recording(False))

    def test_existing_ledger_refuses(self):
        self.ledger.mkdir(parents=True)
        (self.ledger / 'end85.json').write_text('{}', encoding='utf-8')
        with self.assertRaises(FileExistsError):
            self._run()
        self.assertEqual(self.h.actions, [])

    def test_coverage_error_abort(self):
        self.h.drop_at_turn = 86
        with self.assertRaises(RuntimeError):
            self._run()
        self.assertEqual(self.h.actions, [85])
        self.assertTrue(self.h.all_recording(False))

    def test_timeout_and_visibility(self):
        self.h.visibility = lambda h: None
        with self.assertRaises(RuntimeError):
            self._run()
        self.h.visibility = lambda h: False
        self.h.advance = False
        with self.assertRaises(TimeoutError):
            self._run()
        self.assertTrue(self.h.all_recording(False))

if __name__ == '__main__':
    unittest.main()