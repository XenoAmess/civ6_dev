"""Offline filesystem and competing-admission witnesses; no Game or HTTP."""
from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
import json
from pathlib import Path
import tempfile
import subprocess
import sys
import threading
import time
import unittest
from unittest.mock import patch
from unittest.mock import Mock
from tools import performance_admission as pa


class PerformanceAdmissionTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='civ6-admission-')
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()
        self.formal = self.root/'.local-model/p6-formal-performance-active.json'
        self.models = self.root/'.local-model/model-activity'

    def test_multiple_models_allowed_and_all_released(self):
        with pa.model_activity(self.root), pa.model_activity(self.root):
            self.assertEqual(len(list(self.models.iterdir())), 2)
            with self.assertRaises(pa.AdmissionError):
                pa.begin_formal(self.root)
            self.assertFalse(self.formal.exists())
        self.assertEqual(list(self.models.iterdir()), [])

    def test_formal_blocks_model_before_body(self):
        handle = pa.begin_formal(self.root)
        with self.assertRaises(pa.AdmissionError):
            with pa.model_activity(self.root):
                self.fail('Model body must not be entered')
        self.assertFalse(self.models.exists())
        pa.finish_formal(handle)

    def test_model_body_exception_retains_until_explicit_reconciliation(self):
        with self.assertRaises(ValueError):
            with pa.model_activity(self.root) as handle:
                raise ValueError('Unresolved child')
        self.assertTrue(Path(handle['path']).is_file())
        with self.assertRaises(pa.AdmissionError):
            pa.begin_formal(self.root)
        self.assertFalse(self.formal.exists())
        pa.release_model(handle)  # This test has no child; its outcome is known.
        pa.finish_formal(pa.begin_formal(self.root))

    def test_formal_failure_does_not_implicitly_clear_marker(self):
        handle = pa.begin_formal(self.root)
        try:
            raise RuntimeError('Capture unresolved')
        except RuntimeError:
            pass
        with self.assertRaises(pa.AdmissionError):
            with pa.model_activity(self.root):
                self.fail('Formal outcome is still unresolved')
        pa.finish_formal(handle)

    def test_legacy_foreign_formal_preserved(self):
        self.formal.parent.mkdir()
        self.formal.write_bytes(b'{"case":"legacy unknown"}')
        before = self.formal.read_bytes()
        with self.assertRaises(pa.AdmissionError):
            pa.begin_formal(self.root)
        with self.assertRaises(pa.AdmissionError):
            with pa.model_activity(self.root):
                self.fail('Legacy marker must block')
        self.assertEqual(self.formal.read_bytes(), before)

    def test_cleanup_rejects_tampered_nonce_role_and_path(self):
        handle = pa.begin_formal(self.root)
        original = self.formal.read_bytes()
        for key, value in [('nonce', '0'*32), ('role', pa.MODEL), ('path', str(self.root/'other.json'))]:
            wrong = {**handle, key: value}
            with self.assertRaises(pa.AdmissionError):
                pa.finish_formal(wrong)
            self.assertEqual(self.formal.read_bytes(), original)
        pa.finish_formal(handle)

    def test_normal_model_exit_does_not_delete_replaced_record(self):
        changed = None
        with self.assertRaises(pa.AdmissionError):
            with pa.model_activity(self.root) as handle:
                changed = Path(handle['path'])
                changed.write_text('{"role":"MODEL_ACTIVITY","nonce":"foreign"}', encoding='utf-8')
        self.assertIn('foreign', changed.read_text(encoding='utf-8'))

    def test_formal_appears_between_model_checks(self):
        original_write = pa._write
        held = []
        def interleave(path, data):
            if data['role'] == pa.MODEL:
                held.append(pa.begin_formal(self.root))
            original_write(path, data)
        with patch.object(pa, '_write', side_effect=interleave):
            with self.assertRaises(pa.AdmissionError):
                with pa.model_activity(self.root):
                    self.fail('Second formal check must prevent entry')
        self.assertEqual(list(self.models.iterdir()), [])
        self.assertTrue(self.formal.exists())
        pa.finish_formal(held[0])

    def test_formal_scan_failure_rolls_back_only_own_marker(self):
        self.models.mkdir(parents=True)
        original = Path.iterdir
        def denied(path):
            if path == self.models:
                raise PermissionError('Unknown activity')
            return original(path)
        with patch.object(Path, 'iterdir', denied):
            with self.assertRaises(pa.AdmissionError):
                pa.begin_formal(self.root)
        self.assertFalse(self.formal.exists())

    def test_unknown_non_json_entry_blocks_measurement(self):
        self.models.mkdir(parents=True)
        unknown = self.models/'unfinished.tmp'
        unknown.write_bytes(b'unknown')
        with self.assertRaises(pa.AdmissionError):
            pa.begin_formal(self.root)
        self.assertEqual(unknown.read_bytes(), b'unknown')
        self.assertFalse(self.formal.exists())

    def test_metadata_immutable_and_owned_identity_not_overridden(self):
        metadata = {'case': 'real', 'role': 'foreign', 'nonce': 'foreign', 'nested': {'v': 1}}
        before = deepcopy(metadata)
        handle = pa.begin_formal(self.root, metadata)
        record = json.loads(self.formal.read_text(encoding='utf-8'))
        self.assertEqual(record['role'], pa.FORMAL)
        self.assertEqual(record['nonce'], handle['nonce'])
        self.assertEqual(record['case'], 'real')
        self.assertEqual(metadata, before)
        pa.finish_formal(handle)

    def test_competing_admissions_never_enter_simultaneously(self):
        # Finite Windows/Python/thread/filesystem witness; not a hardware proof.
        for round_id in range(24):
            root = self.root/str(round_id)
            barrier = threading.Barrier(2)
            count_lock = threading.Lock()
            active = [0]
            peak = [0]
            def body():
                with count_lock:
                    active[0] += 1
                    peak[0] = max(peak[0], active[0])
                time.sleep(.01)
                with count_lock:
                    active[0] -= 1
            def model():
                barrier.wait(timeout=2)
                try:
                    with pa.model_activity(root):
                        body()
                except pa.AdmissionError:
                    return 'blocked'
            def formal():
                barrier.wait(timeout=2)
                try:
                    handle = pa.begin_formal(root)
                except pa.AdmissionError:
                    return 'blocked'
                body()
                pa.finish_formal(handle)
            with ThreadPoolExecutor(max_workers=2) as pool:
                for future in [pool.submit(model), pool.submit(formal)]:
                    future.result(timeout=3)
            self.assertLessEqual(peak[0], 1)
            self.assertEqual(active[0], 0)

    def test_legacy_formal_drivers_refuse_existing_model_before_query(self):
        from tools.run_observed_acceptance import run as observed
        from tools.run_paired_acceptance import run as paired
        query = Mock(side_effect=AssertionError('No Native query is allowed'))
        with pa.model_activity(self.root):
            # Simulates an older wrapper creating its marker after model entry.
            self.formal.write_text('{"case":"legacy"}', encoding='utf-8')
            with patch.object(Path, 'cwd', return_value=self.root):
                with self.assertRaises(pa.AdmissionError):
                    observed(query, lambda: False, lambda: 0., lambda _: None,
                             lambda _: None, self.root/'observed-ledger')
                with self.assertRaises(pa.AdmissionError):
                    paired(query, lambda: False, lambda: None, lambda: 0.,
                           lambda _: None, lambda _: None, self.root/'paired-ledger',
                           variant='enabled', fixture_sha256='a'*64)
            query.assert_not_called()
            self.formal.unlink()  # This test created the marker; no Native ran.

    def test_actual_cli_rejects_formal_marker_before_missing_inputs(self):
        source = Path(__file__).resolve().parents[1]
        tools_dir = self.root/'tools'
        tools_dir.mkdir()
        (tools_dir/'__init__.py').write_text('', encoding='utf-8')
        for name in ('local_model.py', 'performance_admission.py'):
            (tools_dir/name).write_bytes((source/'tools'/name).read_bytes())
        handle = pa.begin_formal(self.root, {'case': 'software CLI fixture'})
        result = subprocess.run(
            [sys.executable, '-X', 'utf8', str(tools_dir/'local_model.py'),
             '--task', 'missing-task', '--source', 'missing-source',
             '--output-dir', str(self.root/'evidence'), '--max-tokens', '10'],
            cwd=self.root, capture_output=True, shell=False, timeout=10)
        self.assertEqual(result.returncode, 1)
        self.assertIn(b'admission blocked', result.stderr)
        self.assertFalse((self.root/'evidence').exists())
        self.assertFalse(self.models.exists())
        pa.finish_formal(handle)
