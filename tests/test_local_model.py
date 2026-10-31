"""Protocol and retry regressions using a local fake HTTP server, no model calls."""
import contextlib
import errno
import io
import json
from pathlib import Path
import socket
import tempfile
import threading
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from unittest.mock import patch

from tools.local_model import execute, iter_sse_data, main, retry_kind


def stream(content='{"answer":1}', finish='stop', done=True):
    events = [
        {'choices': [{'index': 0, 'delta': {'role': 'assistant', 'content': ''}, 'finish_reason': None}]},
        {'choices': [{'index': 0, 'delta': {'content': content}, 'finish_reason': None}]},
        {'choices': [{'index': 0, 'delta': {}, 'finish_reason': finish}]},
        {'choices': [], 'usage': {'prompt_tokens': 12, 'completion_tokens': 4, 'total_tokens': 16}},
    ]
    return ''.join('data: ' + json.dumps(event) + '\r\n\r\n' for event in events).encode() + (b'data: [DONE]\r\n\r\n' if done else b'')


class LocalModelTests(unittest.TestCase):
    def config(self, url):
        config = json.loads((Path(__file__).resolve().parents[1] / 'docs/local-model-executor-config.json').read_text(encoding='utf-8'))
        config['base_url'] = url
        config['transient_retries'].update(maximum_attempts=2, backoff_seconds=[0], jitter_ratio=0)
        return config

    def exchange(self, replies):
        requests = []

        class Handler(BaseHTTPRequestHandler):
            def do_POST(self):
                requests.append(json.loads(self.rfile.read(int(self.headers['Content-Length']))))
                status, body = replies.pop(0)
                self.send_response(status)
                self.send_header('Content-Length', str(len(body)))
                self.end_headers()
                self.wfile.write(body)

            def log_message(self, *args):
                pass

        server = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        self.addCleanup(server.server_close)
        self.addCleanup(thread.join)
        self.addCleanup(server.shutdown)
        return self.config(f'http://127.0.0.1:{server.server_port}/v1'), requests

    def test_sse_one_shot_iterator_multiline_whitespace_and_utf8(self):
        lines = iter([b': comment\r\n', b'id: 4\r\n', b'data:  a \r\n', b'data:b\r\n', b'\r\n', b'data\n', b'\n'])
        self.assertEqual(list(iter_sse_data(lines)), [' a \nb', ''])
        with self.assertRaises(UnicodeDecodeError):
            list(iter_sse_data(iter([b'data: \xff\n'])))
        with self.assertRaises(TypeError):
            list(iter_sse_data(['data: wrong']))

    def run_exchange(self, replies):
        config, requests = self.exchange(replies)
        with tempfile.TemporaryDirectory() as temp, contextlib.redirect_stdout(io.StringIO()):
            output = Path(temp) / 'run'
            result = execute(config, {'real': 'request'}, output, 3)
            final = json.loads((output / 'result.json').read_text(encoding='utf-8'))
            files = {path.name: path.read_bytes() for path in output.iterdir()}
        return result, final, files, requests

    def test_complete_stream_has_actual_usage_and_separate_metrics(self):
        code, result, files, requests = self.run_exchange([(200, stream())])
        self.assertEqual(code, 0)
        self.assertEqual(result['candidate'], {'answer': 1})
        self.assertEqual(result['usage']['total_tokens'], 16)
        self.assertIsNone(result['cached_prompt_tokens_if_reported'])
        self.assertIsNone(result['adopted'])
        self.assertTrue(result['sse_done'])
        self.assertLessEqual(result['http_headers_ms'], result['first_nonempty_content_delta_ms'])
        self.assertEqual(len(requests), 1)
        self.assertEqual(files['attempt-1.sse'], stream())

    def test_partial_stream_retried_without_candidate_concatenation(self):
        code, result, files, requests = self.run_exchange([(200, stream('{"partial":', done=False)), (200, stream())])
        self.assertEqual(code, 0)
        self.assertEqual(len(requests), 2)
        self.assertEqual(requests[0], requests[1])
        self.assertEqual(result['candidate'], {'answer': 1})
        self.assertEqual(files['attempt-1.content.txt'], b'{"partial":')
        self.assertFalse(json.loads(files['attempt-1.result.json'])['success'])

    def test_transient_http_retried_but_auth_failure_not_retried(self):
        for status, expected_count in [(503, 2), (401, 1)]:
            with self.subTest(status=status):
                code, result, files, requests = self.run_exchange([(status, b'error'), (200, stream())])
                self.assertEqual(len(requests), expected_count)
                self.assertEqual(code, 0 if status == 503 else 1)
                self.assertEqual(files['attempt-1.sse'], b'error')

    def test_length_invalid_json_invalid_utf8_are_permanent(self):
        for response in [stream(finish='length'), stream('not json'), stream('[]'), b'data: \xff\n\n']:
            with self.subTest(response=response):
                code, result, files, requests = self.run_exchange([(200, response), (200, stream())])
                self.assertEqual(code, 1)
                self.assertEqual(len(requests), 1)
                self.assertFalse(result['success'])
                # An invalid first line fails immediately; retain exactly the bytes read.
                self.assertTrue(files['attempt-1.sse'])
                self.assertTrue(response.startswith(files['attempt-1.sse']))

    def test_network_classification_does_not_retry_disk_permission_errors(self):
        self.assertEqual(retry_kind(ConnectionRefusedError(errno.ECONNREFUSED, 'refused')), 'connection_refused')
        self.assertEqual(retry_kind(socket.timeout('slow')), 'read_timeout')
        self.assertIsNone(retry_kind(PermissionError('disk')))

    def test_cli_builds_three_messages_and_preserves_config_defaults(self):
        with tempfile.TemporaryDirectory() as temp, contextlib.redirect_stderr(io.StringIO()):
            root = Path(temp)
            config = self.config('http://127.0.0.1/v1')
            config['defaults']['frequency_penalty'] = 0.3
            (root / 'config.json').write_text(json.dumps(config), encoding='utf-8')
            task = root / 'task.txt'
            task.write_text('Return a JSON candidate for the current source.', encoding='utf-8')
            args = ['--config', str(root / 'config.json'), '--task', str(task), '--source', str(task), '--output-dir', str(root / 'run'), '--max-tokens', '300']
            with patch('tools.local_model.execute', return_value=0) as send:
                self.assertEqual(main(args), 0)
                body = send.call_args.args[1]
                self.assertEqual([message['role'] for message in body['messages']], ['system', 'user', 'user'])
                self.assertEqual(body['frequency_penalty'], 0.3)
                self.assertEqual(body['messages'][0]['content'], config['prompting']['system_template'])
            task.write_text('', encoding='utf-8')
            self.assertEqual(main(args), 1)

    def test_existing_evidence_directory_is_never_overwritten(self):
        with tempfile.TemporaryDirectory() as temp:
            with self.assertRaises(FileExistsError):
                execute(self.config('http://127.0.0.1/v1'), {}, Path(temp), 1)


if __name__ == '__main__':
    unittest.main()
