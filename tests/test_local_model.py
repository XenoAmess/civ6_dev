"""Shared caller adapter boundaries; no HTTP, package updates or game actions."""
import contextlib
import copy
import importlib.util
import io
import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

from tools import local_model as adapter


SHARED_ROOT = adapter.PROJECT_ROOT.parent / 'local-model-operations'
if os.environ.get('LOCAL_MODEL_OPERATIONS_ROOT'):
    SHARED_ROOT = Path(os.environ['LOCAL_MODEL_OPERATIONS_ROOT']).resolve()
spec = importlib.util.spec_from_file_location('civ6_shared_call', SHARED_ROOT / 'scripts/call.py')
shared_call = importlib.util.module_from_spec(spec)
spec.loader.exec_module(shared_call)


class LocalModelTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='civ6 adapter test ')
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.shared = self.root / 'relocated shared repo'
        for name in ('AGENTS.md', 'scripts/call.py', 'scripts/check_opencode.py'):
            path = self.shared / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text('fixture, not executed', encoding='utf-8')
        self.config = copy.deepcopy(shared_call.read_json(SHARED_ROOT / 'config/executor.json'))
        self.config['base_url'] = 'http://fixture.invalid:4567/v1'
        self.config['model'] = 'fixture-model'
        self.config['defaults']['frequency_penalty'] = 0.3
        self.config_path = self.shared / 'config/executor.json'
        self.config_path.parent.mkdir(parents=True)
        self.save(self.config_path, self.config)
        self.manifest = copy.deepcopy(adapter.read_json(adapter.DEFAULT_CONFIG))
        self.manifest['prompting']['system_template'] = 'Civ6 test context'
        self.manifest_path = self.root / 'project manifest.json'
        self.save(self.manifest_path, self.manifest)
        self.task = self.root / 'actual task.txt'
        self.task.write_text('Review this unfinished source; return JSON.\n', encoding='utf-8-sig')
        self.a = self.root / 'a source.lua'
        self.z = self.root / 'z source.lua'
        self.a.write_text('local value = "白绮"\n', encoding='utf-8-sig')
        self.z.write_text('return value\n', encoding='utf-8')
        self.output = self.root / 'new evidence'
        self.args = ['--config', str(self.manifest_path), '--task', str(self.task),
                     '--source', str(self.z), '--source', str(self.a), '--source', str(self.a),
                     '--output-dir', str(self.output), '--max-tokens', '300']
        self.addCleanup(patch.stopall)
        patch.dict(os.environ, {'LOCAL_MODEL_OPERATIONS_ROOT': str(self.shared)}, clear=False).start()
        patch.object(adapter, 'shared_revision', return_value='fixture-commit').start()
        self.observed = []

    @staticmethod
    def save(path, value):
        path.write_text(json.dumps(value, ensure_ascii=False), encoding='utf-8')

    def run_cli(self, args=None, fake=None):
        with contextlib.redirect_stderr(io.StringIO()), patch.object(adapter.subprocess, 'run', side_effect=fake or self.exchange) as runner:
            code = adapter.main(args or self.args)
        return code, runner

    def exchange(self, argv, **kwargs):
        self.assertIsInstance(argv, list)
        self.assertEqual(kwargs, {'shell': False})
        self.assertEqual(Path(argv[3]), self.shared / 'scripts/call.py')
        config = adapter.read_json(argv[argv.index('--config') + 1])
        # Real canonical request consumer, not a duplicate homemade spec parser.
        request, original_system = shared_call.prepare_request(argv[4], config)
        self.observed.append((argv, config, request))
        self.output.mkdir(parents=True)
        content = self.output / 'ATTEMPT1-CONTENT.txt'
        content.write_text('{"candidate":"do not execute"}', encoding='utf-8')
        summary = {'success': True, 'adopted': False, 'attempts': [
            {'candidate_complete': True, 'finish_reason': 'stop', 'sse_done': True,
             'failure': None, 'content_path': str(content), 'usage': None,
             'cached_prompt_tokens_if_reported': None, 'adopted': False}]}
        self.save(self.output / 'SUMMARY.json', summary)
        (self.output / 'ATTEMPT1-RESPONSE.sse').write_bytes(b'canonical raw fixture')
        return subprocess.CompletedProcess(argv, 0)

    def test_live_shared_authority_and_real_canonical_request_consumer(self):
        code, runner = self.run_cli()
        self.assertEqual(code, 0)
        self.assertEqual(runner.call_count, 1)
        argv, effective, request = self.observed[0]
        expected = copy.deepcopy(self.config)
        expected['prompting']['system_template'] = 'Civ6 test context'
        self.assertEqual(effective, expected)
        self.assertEqual(request['frequency_penalty'], 0.3)
        self.assertEqual(request['model'], 'fixture-model')
        self.assertEqual(request['max_tokens'], 300)
        self.assertEqual(request['stream_options'], {'include_usage': True})
        self.assertEqual([x['role'] for x in request['messages']], ['system', 'user', 'user'])
        stable = 'FILE ' + self.a.as_posix() + '\nlocal value = "白绮"\n\n\nFILE ' + self.z.as_posix() + '\nreturn value\n'
        self.assertEqual(request['messages'][1]['content'], stable)
        self.assertEqual(request['messages'][2]['content'], self.task.read_text(encoding='utf-8-sig'))
        self.assertNotIn('fixture-commit', request['messages'][1]['content'])
        provenance = adapter.read_json(self.output / 'ADAPTER-PROVENANCE.json')
        self.assertEqual(provenance['shared_commit'], 'fixture-commit')
        self.assertIsNone(provenance['timeout_override'])

    def test_live_config_update_used_without_endpoint_or_model_fork(self):
        self.config['model'] = 'updated-model'
        self.config['base_url'] = 'https://changed.invalid/v1'
        self.save(self.config_path, self.config)
        self.assertEqual(self.run_cli()[0], 0)
        self.assertEqual(self.observed[0][1]['base_url'], 'https://changed.invalid/v1')
        self.assertEqual(self.observed[0][2]['model'], 'updated-model')

    def test_explicit_timeout_changes_only_shared_read_timeout(self):
        self.assertEqual(self.run_cli(self.args + ['--timeout', '42.5'])[0], 0)
        expected = copy.deepcopy(self.config)
        expected['prompting']['system_template'] = 'Civ6 test context'
        expected['timeouts']['read_seconds'] = 42.5
        self.assertEqual(self.observed[0][1], expected)

    def test_invalid_arguments_and_empty_or_missing_input_fail_before_subprocess(self):
        for flag, value in [('--max-tokens', '0'), ('--max-tokens', '16001'),
                            ('--timeout', 'nan'), ('--timeout', 'inf'), ('--timeout', '0'), ('--timeout', '3601')]:
            with self.subTest(flag=flag, value=value):
                code, runner = self.run_cli(self.args + [flag, value])
                self.assertEqual(code, 1)
                runner.assert_not_called()
        self.task.write_text(' \n', encoding='utf-8')
        self.assertEqual(self.run_cli()[0], 1)
        self.task.unlink()
        code, runner = self.run_cli()
        self.assertEqual(code, 1)
        runner.assert_not_called()
        self.assertFalse(self.output.exists())

    def test_existing_evidence_directory_is_untouched(self):
        self.output.mkdir()
        marker = self.output / 'DISPATCH.claim'
        marker.write_bytes(b'original owner')
        code, runner = self.run_cli()
        self.assertEqual(code, 1)
        runner.assert_not_called()
        self.assertEqual(marker.read_bytes(), b'original owner')
        self.assertEqual(list(self.output.iterdir()), [marker])

    def test_missing_dependency_and_old_config_fail_closed(self):
        (self.shared / 'scripts/check_opencode.py').unlink()
        code, runner = self.run_cli()
        self.assertEqual(code, 1)
        runner.assert_not_called()
        self.save(self.manifest_path, self.config)
        code, runner = self.run_cli()
        self.assertEqual(code, 1)
        runner.assert_not_called()

    def test_sibling_resolution_does_not_depend_on_cwd(self):
        with patch.dict(os.environ, {}, clear=True), patch.object(adapter, 'PROJECT_ROOT', self.root / 'consumer'):
            manifest = {'shared_repository': {'sibling_path': '../relocated shared repo'}}
            self.assertEqual(adapter.resolve_shared(manifest), self.shared)

    def test_cli_exit_75_and_other_entry_failures_propagate_without_retry(self):
        for expected in (75, 2):
            with self.subTest(expected=expected):
                code, runner = self.run_cli(fake=lambda argv, **kwargs: subprocess.CompletedProcess(argv, expected))
                self.assertEqual(code, expected)
                self.assertEqual(runner.call_count, 1)
                self.assertFalse(self.output.exists())

    def test_real_canonical_cli_checks_maintenance_before_dispatch(self):
        class RepairRequired(OSError):
            repair_request = {'status': 'AI_REPAIR_REQUIRED', 'reason': 'simulated preflight failure'}
        config_path = self.config_path
        with patch.object(shared_call, 'client_preflight', side_effect=RepairRequired()), patch.object(shared_call, 'dispatch') as dispatch, contextlib.redirect_stderr(io.StringIO()) as errors:
            returned = shared_call.main(['nonexistent-spec.json', 'gate-test', '--config', str(config_path), '--output', str(self.output)])
        self.assertEqual(returned, 75)
        dispatch.assert_not_called()
        self.assertIn('AI_REPAIR_REQUIRED', errors.getvalue())
        self.assertFalse(self.output.exists())

    def test_ready_candidate_is_not_adoption_and_does_not_alter_canonical_evidence(self):
        code, runner = self.run_cli()
        self.assertEqual(code, 0)
        result = adapter.read_json(self.output / 'result.json')
        self.assertEqual(result['candidate'], {'candidate': 'do not execute'})
        self.assertIsNone(result['adopted'])
        self.assertIsNone(result['cached_prompt_tokens_if_reported'])
        self.assertFalse(adapter.read_json(self.output / 'SUMMARY.json')['adopted'])
        self.assertEqual((self.output / 'ATTEMPT1-RESPONSE.sse').read_bytes(), b'canonical raw fixture')

    def test_reject_json_nonobjects_nonfinite_duplicates_and_invalid_json(self):
        for text in ('[]', 'null', 'invalid', '{"x":NaN}', '{"x":1,"x":2}'):
            with self.subTest(text=text):
                def exchange(argv, **kwargs):
                    result = self.exchange(argv, **kwargs)
                    (self.output / 'ATTEMPT1-CONTENT.txt').write_text(text, encoding='utf-8')
                    return result
                self.output = self.root / ('invalid-' + str(len(self.observed)))
                args = self.args + ['--output-dir', str(self.output)]
                code, runner = self.run_cli(args, fake=exchange)
                self.assertEqual(code, 1)
                self.assertIsNone(adapter.read_json(self.output / 'result.json')['candidate'])
                self.assertEqual((self.output / 'ATTEMPT1-CONTENT.txt').read_text(encoding='utf-8'), text)

    def test_length_missing_done_and_failed_summary_never_parse_partial_candidate(self):
        for change in ({'finish_reason': 'length'}, {'sse_done': False}, {'candidate_complete': False}, {'failure': 'read timeout'}):
            with self.subTest(change=change):
                self.output = self.root / ('partial-' + str(len(self.observed)))
                def exchange(argv, **kwargs):
                    result = self.exchange(argv, **kwargs)
                    summary_path = self.output / 'SUMMARY.json'
                    summary = adapter.read_json(summary_path)
                    summary['attempts'][0].update(change)
                    self.save(summary_path, summary)
                    return result
                with patch.object(adapter, 'strict_object', side_effect=AssertionError('must not parse incomplete candidate')):
                    code, runner = self.run_cli(self.args + ['--output-dir', str(self.output)], fake=exchange)
                self.assertEqual(code, 1)
                self.assertEqual(runner.call_count, 1)

    def test_candidate_path_outside_evidence_is_rejected(self):
        def exchange(argv, **kwargs):
            result = self.exchange(argv, **kwargs)
            summary_path = self.output / 'SUMMARY.json'
            summary = adapter.read_json(summary_path)
            summary['attempts'][0]['content_path'] = str(self.task)
            self.save(summary_path, summary)
            return result
        self.assertEqual(self.run_cli(fake=exchange)[0], 1)
        self.assertIn('outside', adapter.read_json(self.output / 'result.json')['error'])

    def test_identity_and_stop_file_are_cli_metadata_not_prompt(self):
        args = self.args + ['--machine-id', 'test-machine', '--owner', 'test-owner', '--task-id', 'real-task', '--stop-file', str(self.root / 'STOP.json')]
        self.assertEqual(self.run_cli(args)[0], 0)
        argv, config, request = self.observed[0]
        self.assertEqual(argv[5], 'real-task')
        self.assertEqual(argv[argv.index('--machine-id') + 1], 'test-machine')
        self.assertEqual(argv[argv.index('--owner') + 1], 'test-owner')
        self.assertEqual(argv[argv.index('--stop-file') + 1], str(self.root / 'STOP.json'))
        self.assertNotIn('test-owner', json.dumps(request))


if __name__ == '__main__':
    unittest.main()
