import copy
from datetime import datetime, timezone, timedelta
import json
from pathlib import Path
import tempfile
import threading
import unittest

from tools.native_console_audit import (
    QueryRecorder, audit_transactions, code_digest, intersects_window, marker_rows,
)


class QueryRecordingTests(unittest.TestCase):
    def test_success_records_before_delegate_and_preserves_return_identity(self):
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary) / 'records'
            result = [{'tag': -1, 'payload': 'actual delegate return'}]
            calls = []

            def delegate(context, code):
                calls.append((context, code))
                self.assertTrue((directory / '000001-attempt.json').is_file())
                self.assertFalse((directory / '000001-returned.json').exists())
                return result

            record = QueryRecorder(directory, delegate, lambda: {'role': 'UNIT_TEST_ONLY'})
            self.assertIs(record('Context', 'authored source'), result)
            self.assertEqual(calls, [('Context', 'authored source')])
            attempt = json.loads((directory / '000001-attempt.json').read_bytes())
            returned = json.loads((directory / '000001-returned.json').read_bytes())
            self.assertEqual(attempt['authored_code'], 'authored source')
            self.assertEqual(attempt['code_sha256'], code_digest('authored source'))
            self.assertEqual(returned['messages'], result)
            self.assertEqual((attempt['action_retries'], returned['action_retries']), (0, 0))

    def test_delegate_exception_is_recorded_once_and_same_exception_propagates(self):
        with tempfile.TemporaryDirectory() as temporary:
            error = ConnectionResetError('unit test transport interruption')
            calls = []

            def delegate(*args):
                calls.append(args)
                raise error

            record = QueryRecorder(Path(temporary) / 'records', delegate, lambda: {})
            with self.assertRaises(ConnectionResetError) as caught:
                record('Context', 'source')
            self.assertIs(caught.exception, error)
            self.assertEqual(len(calls), 1)
            returned = json.loads((record.directory / '000001-returned.json').read_bytes())
            self.assertEqual(returned['exception_type'], 'ConnectionResetError')
            self.assertFalse(record.in_flight)

    def test_nested_delegate_cannot_issue_a_second_call(self):
        with tempfile.TemporaryDirectory() as temporary:
            calls = []

            def delegate(*args):
                calls.append(args)
                with self.assertRaisesRegex(RuntimeError, 'nested'):
                    record('Other', 'second source')
                return []

            record = QueryRecorder(Path(temporary) / 'records', delegate, lambda: {})
            record('Context', 'first source')
            self.assertEqual(len(calls), 1)
            self.assertEqual(record.sequence, 1)

    def test_exclusive_directory_and_invalid_metadata_fail_before_transport(self):
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary) / 'records'
            calls = []
            record = QueryRecorder(directory, lambda *a: calls.append(a), lambda: {'utc': 'forged'})
            with self.assertRaises(ValueError):
                record('Context', 'source')
            with self.assertRaises(FileExistsError):
                QueryRecorder(directory, lambda *a: None, lambda: {})
            self.assertEqual(calls, [])
            self.assertEqual(list(directory.iterdir()), [])

    def test_second_thread_cannot_pass_while_first_is_still_in_metadata(self):
        with tempfile.TemporaryDirectory() as temporary:
            entered, release = threading.Event(), threading.Event()
            calls, failures = [], []

            def metadata():
                entered.set()
                self.assertTrue(release.wait(5))
                return {}

            record = QueryRecorder(Path(temporary) / 'records', lambda *a: calls.append(a) or [], metadata)

            def first():
                try:
                    record('Context', 'first source')
                except BaseException as error:
                    failures.append(error)

            thread = threading.Thread(target=first)
            thread.start()
            try:
                self.assertTrue(entered.wait(5))
                with self.assertRaisesRegex(RuntimeError, 'Concurrent'):
                    record('Context', 'second source')
            finally:
                release.set()
                thread.join(5)
            self.assertFalse(thread.is_alive())
            self.assertEqual(failures, [])
            self.assertEqual(calls, [('Context', 'first source')])


class IntervalAuditTests(unittest.TestCase):
    """Synthetic clock/receipt data; no game API or Native-effect credit."""

    def fixture(self):
        origin = datetime(2026, 11, 25, tzinfo=timezone.utc)
        iso = lambda seconds: (origin + timedelta(seconds=seconds)).isoformat()
        owner = {'pid': 123, 'created_at': 456.0, 'exe': 'UNIT_TEST_ONLY'}
        code = 'unit-test authored source'
        attempt = dict(sequence=1, utc=iso(50), owner=owner, source_version=184,
                       context='Context', authored_code=code, code_sha256=code_digest(code),
                       role='UNIT_TEST_ONLY', delegate_invocations=1, action_retries=0)
        returned = dict(sequence=1, utc=iso(50.1), messages=[], action_retries=0)
        return dict(attempts=[dict(attempt=attempt, returned=returned)],
                    wires=[dict(name='wire-1', utc=iso(50.05), context='Context',
                                authored_code=code, sha256='unit-test-wire-sha')],
                    anchors={7: 1100, 8: 1120, 9: 1140, 10: 1160, 11: 1180},
                    calibrations=[dict(host_start=iso(t), host_end=iso(t+.01),
                                       actual_game_now=1000+t+.005) for t in range(5, 36, 5)],
                    owner=owner, source_version=184, arm_utc=iso(40),
                    endpoints=[dict(owner=owner, utc=iso(1), no_CMD_sent=True)])

    def test_complete_outside_window_data_qualifies_without_mutation(self):
        data = self.fixture()
        old = copy.deepcopy(data)
        result = audit_transactions(**data)
        self.assertTrue(result['quiet_observer_qualified'])
        self.assertEqual(result['actual_matched_wire_receipts'], 1)
        self.assertEqual(data, old)

    def test_unknown_unowned_duplicate_and_reused_wire_are_not_qualified(self):
        for mutation in ('missing', 'unowned', 'duplicate_match', 'reused'):
            with self.subTest(mutation=mutation):
                data = self.fixture()
                if mutation == 'missing':
                    data['wires'] = []
                elif mutation in ('unowned', 'duplicate_match'):
                    extra = dict(data['wires'][0], name='wire-2')
                    if mutation == 'unowned':
                        extra['authored_code'] = 'different actual source'
                    data['wires'].append(extra)
                else:
                    item = copy.deepcopy(data['attempts'][0])
                    item['attempt']['sequence'] = item['returned']['sequence'] = 2
                    data['attempts'].append(item)
                self.assertFalse(audit_transactions(**data)['quiet_observer_qualified'])

    def test_full_host_call_overlapping_window_is_retained_and_rejected(self):
        data = self.fixture()
        # Extend the recorded call into the first window; no sample is removed.
        origin = datetime.fromisoformat(data['attempts'][0]['attempt']['utc'])
        data['attempts'][0]['returned']['utc'] = (origin + timedelta(seconds=50.1)).isoformat()
        result = audit_transactions(**data)
        self.assertFalse(result['quiet_observer_qualified'])
        self.assertEqual(result['overlap_transactions'][0]['window_overlaps'], [7])
        self.assertEqual(len(result['transactions']), 1)

    def test_clock_inconsistency_and_late_or_missing_endpoint_reject(self):
        for mutation in ('clock', 'late_endpoint', 'missing_endpoint'):
            with self.subTest(mutation=mutation):
                data = self.fixture()
                if mutation == 'clock':
                    data['calibrations'][-1]['actual_game_now'] += 1
                elif mutation == 'late_endpoint':
                    data['endpoints'][0]['utc'] = data['arm_utc']
                else:
                    data['endpoints'] = []
                self.assertFalse(audit_transactions(**data)['quiet_observer_qualified'])

    def test_owner_source_code_sequence_and_raw_id_malformed_records_fail(self):
        for mutation in ('owner', 'source', 'code', 'sequence', 'duplicate_wire_name', 'nan', 'naive'):
            with self.subTest(mutation=mutation):
                data = self.fixture()
                item = data['attempts'][0]
                if mutation == 'owner':
                    item['attempt']['owner'] = {'pid': 999}
                elif mutation == 'source':
                    item['attempt']['source_version'] = 172
                elif mutation == 'code':
                    item['attempt']['authored_code'] += ' changed'
                elif mutation == 'sequence':
                    item['attempt']['sequence'] = item['returned']['sequence'] = 2
                elif mutation == 'duplicate_wire_name':
                    data['wires'].append(dict(data['wires'][0]))
                elif mutation == 'nan':
                    data['calibrations'][0]['actual_game_now'] = float('nan')
                else:
                    data['calibrations'][0]['host_start'] = '2026-11-25T00:00:00'
                with self.assertRaises(ValueError):
                    audit_transactions(**data)

    def test_interval_boundaries_and_quantization_are_conservative(self):
        self.assertFalse(intersects_window(1, 2, 20, 0, 0))
        self.assertTrue(intersects_window(19.9, 20.1, 20, 0, 0))
        self.assertTrue(intersects_window(29.9, 30.1, 20, 0, 0))
        self.assertTrue(intersects_window(19, 19.5, 20, 0, 1))
        with self.assertRaises(ValueError):
            intersects_window(2, 1, 20, 0, 0)
        with self.assertRaises(ValueError):
            intersects_window(True, 2, 20, 0, 0)

    def test_multiline_markers_are_exact_and_ignore_other_tags(self):
        messages = [dict(tag=-1, payload='O\0Context: STATE\t1\t2\nContext: OTHER\t3'),
                    dict(tag=-1, payload='Context: STATE_SUFFIX\t4'),
                    dict(tag=3, payload='Context: STATE\t5')]
        self.assertEqual(marker_rows(messages, 'STATE'), [['1', '2']])


if __name__ == '__main__':
    unittest.main()
