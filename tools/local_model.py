"""Save auditable local-model candidates; never execute their contents."""
import argparse
import datetime
import errno
import http.client
import json
from pathlib import Path
import random
import socket
import sys
import time
import urllib.error
import urllib.request


def write_json(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')


def iter_sse_data(lines):
    # Local-model parser candidate, corrected to avoid consuming a one-shot iterator.
    event_data = []
    for line in lines:
        if not isinstance(line, bytes):
            raise TypeError('SSE lines must be bytes')
        text = line.removesuffix(b'\n').removesuffix(b'\r').decode('utf-8')
        if text == '':
            if event_data:
                yield '\n'.join(event_data)
                event_data = []
            continue
        if text.startswith(':'):
            continue
        field, _, value = text.partition(':')
        if field == 'data':
            event_data.append(value.removeprefix(' '))
    if event_data:
        yield '\n'.join(event_data)


def consume_stream(lines, state, start):
    for data in iter_sse_data(lines):
        if data == '[DONE]':
            state['sse_done'] = True
            break
        event = json.loads(data)
        if not isinstance(event, dict) or 'error' in event:
            raise ValueError('Invalid SSE object or server error event')
        if event.get('usage') is not None:
            if not isinstance(event['usage'], dict):
                raise ValueError('Invalid usage object')
            state['usage'] = event['usage']
        choices = event.get('choices', [])
        if not isinstance(choices, list):
            raise ValueError('Invalid choices')
        for choice in choices:
            if not isinstance(choice, dict) or choice.get('index', 0) != 0:
                raise ValueError('Expected only choice index 0')
            delta = choice.get('delta', {})
            if not isinstance(delta, dict):
                raise ValueError('Invalid delta')
            content = delta.get('content')
            if content is not None and not isinstance(content, str):
                raise ValueError('Expected string content')
            if content:
                if state['first_nonempty_content_delta_ms'] is None:
                    state['first_nonempty_content_delta_ms'] = (time.perf_counter() - start) * 1000
                state['parts'].append(content)
            if choice.get('finish_reason') is not None:
                state['finish_reason'] = choice['finish_reason']
    if state['finish_reason'] not in (None, 'stop'):
        raise ValueError(f"Unusable finish_reason: {state['finish_reason']}")
    if not state['sse_done'] or state['finish_reason'] is None:
        raise EOFError('Incomplete SSE; no complete stop/[DONE] pair')
    candidate = json.loads(''.join(state['parts']))
    if not isinstance(candidate, dict):
        raise ValueError('Candidate must be a JSON object')
    return candidate


def retry_kind(exc):
    if isinstance(exc, urllib.error.HTTPError):
        return None
    if isinstance(exc, urllib.error.URLError):
        exc = exc.reason
    if isinstance(exc, (socket.timeout, TimeoutError)):
        return 'read_timeout'
    if isinstance(exc, (EOFError, http.client.IncompleteRead, http.client.RemoteDisconnected)):
        return 'incomplete_response'
    if isinstance(exc, OSError):
        if exc.errno == errno.ECONNREFUSED or getattr(exc, 'winerror', None) == 10061:
            return 'connection_refused'
        if exc.errno in (errno.ECONNRESET, errno.ECONNABORTED, errno.EPIPE) or getattr(exc, 'winerror', None) in (10054, 10053):
            return 'connection_reset'
        if exc.errno == errno.ETIMEDOUT or getattr(exc, 'winerror', None) == 10060:
            return 'connect_timeout'
    return None


def execute(config, body, output, timeout):
    output.mkdir(parents=True, exist_ok=False)
    write_json(output / 'request.json', body)
    request_bytes = json.dumps(body, ensure_ascii=False).encode('utf-8')
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    policy = config['transient_retries']

    def record(event):
        event = {**event, 'at_utc': datetime.datetime.now(datetime.timezone.utc).isoformat()}
        with (output / 'events.jsonl').open('a', encoding='utf-8') as file:
            file.write(json.dumps(event, ensure_ascii=False) + '\n')
        print(json.dumps(event, ensure_ascii=True), flush=True)

    for attempt in range(1, policy['maximum_attempts'] + 1):
        start = time.perf_counter()
        state = {'attempt': attempt, 'http_status': None, 'http_headers_ms': None,
                 'first_nonempty_content_delta_ms': None, 'sse_done': False,
                 'finish_reason': None, 'usage': None, 'parts': [], 'adopted': None}
        record({'event': 'BEGIN', 'attempt': attempt})
        retry = False
        with (output / f'attempt-{attempt}.sse').open('wb') as raw:
            try:
                request = urllib.request.Request(config['base_url'].rstrip('/') + '/chat/completions',
                                                 data=request_bytes, headers={'Content-Type': 'application/json'})
                with opener.open(request, timeout=timeout) as response:
                    state['http_headers_ms'] = (time.perf_counter() - start) * 1000
                    state['http_status'] = response.status
                    write_json(output / f'attempt-{attempt}.headers.json', dict(response.headers))

                    def lines():
                        for line in response:
                            raw.write(line)
                            yield line

                    candidate = consume_stream(lines(), state, start)
                state.update(success=True, candidate=candidate)
            except urllib.error.HTTPError as exc:
                state['http_status'] = exc.code
                state['http_headers_ms'] = (time.perf_counter() - start) * 1000
                write_json(output / f'attempt-{attempt}.headers.json', dict(exc.headers))
                try:
                    raw.write(exc.read())
                except (OSError, http.client.HTTPException) as body_error:
                    state['error_body_read_error'] = str(body_error)
                finally:
                    exc.close()
                state.update(success=False, error=f'HTTP {exc.code}')
                retry = exc.code in policy['retry_http_statuses']
            except Exception as exc:
                state.update(success=False, error=f'{type(exc).__name__}: {exc}')
                retry = retry_kind(exc) in policy['retry_transport_errors']
        state['total_ms'] = (time.perf_counter() - start) * 1000
        usage = state['usage'] or {}
        state['cached_prompt_tokens_if_reported'] = (usage.get('prompt_tokens_details') or {}).get('cached_tokens')
        state['content'] = ''.join(state.pop('parts'))
        (output / f'attempt-{attempt}.content.txt').write_text(state['content'], encoding='utf-8')
        state['will_retry'] = retry and attempt < policy['maximum_attempts']
        write_json(output / f'attempt-{attempt}.result.json', state)
        record({'event': 'END', **{key: value for key, value in state.items() if key not in ('content', 'candidate')}})
        write_json(output / 'result.json', state)
        if state['success'] or not state['will_retry']:
            return 0 if state['success'] else 1
        delay = policy['backoff_seconds'][attempt - 1]
        delay *= 1 + random.uniform(-policy['jitter_ratio'], policy['jitter_ratio'])
        record({'event': 'BACKOFF', 'attempt': attempt, 'seconds': delay})
        time.sleep(delay)
    return 1


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--task', required=True, type=Path)
    parser.add_argument('--source', action='append', required=True, type=Path)
    parser.add_argument('--output-dir', required=True, type=Path)
    parser.add_argument('--max-tokens', required=True, type=int)
    parser.add_argument('--timeout', default=900, type=float, help='Socket I/O timeout, seconds')
    parser.add_argument('--config', type=Path, default=Path(__file__).resolve().parents[1] / 'docs/local-model-executor-config.json')
    args = parser.parse_args(argv)
    try:
        if not 1 <= args.max_tokens <= 16000 or not 0 < args.timeout <= 3600:
            raise ValueError('max-tokens must be 1..16000; timeout must be >0 and <=3600')
        config = json.loads(args.config.read_text(encoding='utf-8'))
        if not config['base_url'].startswith(('http://', 'https://')) or not config['model']:
            raise ValueError('Invalid base_url/model')
        if config['authentication']['required']:
            raise ValueError('This caller supports the configured unauthenticated local service only')
        policy = config['transient_retries']
        attempts = policy['maximum_attempts']
        if not isinstance(attempts, int) or not 1 <= attempts <= 6:
            raise ValueError('maximum_attempts must be 1..6')
        delays = policy['backoff_seconds']
        if len(delays) < attempts - 1 or any(not isinstance(x, (int, float)) or not 0 <= x <= 3600 for x in delays):
            raise ValueError('Invalid retry backoff')
        if not 0 <= policy['jitter_ratio'] <= 1:
            raise ValueError('Invalid jitter_ratio')
        if not isinstance(policy['retry_http_statuses'], list) or not isinstance(policy['retry_transport_errors'], list):
            raise ValueError('Retry policies must be lists')
        task = args.task.read_text(encoding='utf-8-sig')
        if not task.strip():
            raise ValueError('Task must be nonempty UTF-8 text')
        system = config['prompting']['system_template']
        if not isinstance(system, str) or not system.strip():
            raise ValueError('Missing system template')
        sources = '\n\n'.join(f'FILE {path.as_posix()}\n{path.read_text(encoding="utf-8-sig")}'
                               for path in sorted(set(args.source), key=lambda path: path.as_posix()))
        body = {**config['defaults'], 'model': config['model'], 'max_tokens': args.max_tokens,
                'stream': True, 'stream_options': {'include_usage': True},
                'messages': [{'role': 'system', 'content': system}, {'role': 'user', 'content': sources},
                             {'role': 'user', 'content': task}]}
        return execute(config, body, args.output_dir, args.timeout)
    except (OSError, ValueError, KeyError, TypeError) as exc:
        print(f'Error: {exc}', file=sys.stderr)
        return 1


if __name__ == '__main__':
    sys.exit(main())
