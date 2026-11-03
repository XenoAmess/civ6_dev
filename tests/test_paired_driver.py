import unittest
from lupa.lua53 import LuaError
from paired_driver_harness import Harness
from tools.run_paired_acceptance import run


def execute(h):return run(h.query,h.visible,h.close,h.now,h.sleep,h.emit,h.ledger,variant='enabled',fixture_sha256='1'*64)


class PairedDriverTests(unittest.TestCase):
    def test_actual_clock_five_ends_and_windows_no_end90(self):
        h=Harness();result=execute(h)
        self.assertEqual(list(h.t.actions.values()),[85,86,87,88,89]);self.assertEqual(result['requested_turns'],[85,86,87,88,89])
        self.assertEqual([x['to_turn'] for x in result['records']],list(range(86,91)))
        self.assertEqual([x['seconds'] for x in result['records']],[2]*5)
        self.assertTrue(all(b['started']>=a['ended']+10 for a,b in zip(result['records'],result['records'][1:])))
        self.assertGreaterEqual(h.now()-result['records'][-1]['ended'],10)
        self.assertEqual(h.lua.globals().P6PairStage.phase,'COMPLETE');self.assertTrue(h.lua.globals().P6PairClock.Snapshot(h.lua.globals().P6PairClock).retired)

    def test_visit_after_end87_one_qa_close_and_hidden_confirmation(self):
        h=Harness(visit=True);result=execute(h)
        self.assertEqual(h.close_calls,1);self.assertEqual(result['requested_turns'],[85,86,87,88,89])
        self.assertIn('TEST_PLAYER_PAIR_DIPLOMACY_CLOSE_REQUESTED',h.messages)
        self.assertIn('TEST_PLAYER_PAIR_DIPLOMACY_HIDDEN_CONFIRMED',h.messages)
        self.assertEqual(len(list(h.ledger.glob('diplomacy-*.json'))),1)

    def test_unknown_end_ack_never_replays_and_only_retires_diagnostic(self):
        h=Harness(lose_end=85)
        with self.assertRaises(OSError):execute(h)
        self.assertEqual(list(h.t.actions.values()),[85]);self.assertEqual(h.lua.globals().P6PairStage.phase,'ABORTED')
        self.assertTrue(h.lua.globals().P6PairClock.Snapshot(h.lua.globals().P6PairClock).retired)
        self.assertEqual(len(list(h.ledger.glob('end-*.json'))),1)

    def test_unknown_qa_close_does_not_retry_or_issue_end88(self):
        h=Harness(visit=True,close_unknown=True)
        with self.assertRaises(OSError):execute(h)
        self.assertEqual(h.close_calls,1);self.assertEqual(list(h.t.actions.values()),[85,86,87])
        self.assertEqual(h.lua.globals().P6PairStage.phase,'ABORTED')

    def test_bad_clock_before_end_submits_no_world_action(self):
        h=Harness();h.t.clockFailAt=2
        with self.assertRaises(LuaError):execute(h)
        self.assertEqual(len(h.t.actions),0);self.assertEqual(h.lua.globals().P6PairStage.phase,'ABORTED')

    def test_setup_clock_failure_skips_foreign_diagnostic_without_claiming_retired(self):
        h=Harness();h.t.clockError=True
        with self.assertRaises(LuaError):execute(h)
        self.assertIsNone(h.lua.globals().P6PairStage);self.assertEqual(len(h.t.actions),0)
        self.assertFalse(h.lua.globals().P6PairClock.Snapshot(h.lua.globals().P6PairClock).retired)
        self.assertIn('PAIR_ABORT_RETIRE_RECEIPT ["SKIPPED_FOREIGN"]',h.messages)

    def test_activation_timeout_preserves_unknown_pending_no_replay(self):
        h=Harness(never_activate=True)
        with self.assertRaises(TimeoutError):execute(h)
        self.assertEqual(list(h.t.actions.values()),[85]);self.assertIsNotNone(h.lua.globals().P6PairClock.Snapshot(h.lua.globals().P6PairClock).pending)

    def test_old_ledger_and_current_diplomacy_refuse_before_any_action(self):
        h=Harness();h.ledger.mkdir(parents=True)
        with self.assertRaises(FileExistsError):execute(h)
        self.assertEqual(len(h.t.actions),0)
        h2=Harness();h2.t.diplomacy=True
        with self.assertRaises(RuntimeError):execute(h2)
        self.assertEqual(len(h2.t.actions),0);self.assertEqual(h2.close_calls,0)


if __name__=='__main__':unittest.main()
