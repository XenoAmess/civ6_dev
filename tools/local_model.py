"""Civ6 candidate adapter to local-model-operations; never execute candidates."""
import argparse
import copy
import hashlib
import json
import math
import os
from pathlib import Path
import subprocess
import sys
import tempfile


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CONFIG = PROJECT_ROOT / 'docs/local-model-executor-config.json'


def read_json(path):
    return json.loads(Path(path).read_text(encoding='utf-8-sig'))


def write_json(path, value):
    with Path(path).open('x', encoding='utf-8', newline='\n') as output:
        output.write(json.dumps(value, ensure_ascii=False, indent=2) + '\n')


def resolve_shared(project):
    selected = os.environ.get('LOCAL_MODEL_OPERATIONS_ROOT')
    root = Path(selected).resolve() if selected else PROJECT_ROOT.joinpath(project['shared_repository']['sibling_path']).resolve()
    for name in ('AGENTS.md', 'config/executor.json', 'scripts/call.py', 'scripts/check_opencode.py'):
        if not root.joinpath(name).is_file():
            raise ValueError('Missing local-model-operations dependency: ' + str(root / name))
    return root


def shared_revision(root):
    try:
        result = subprocess.run(['git', '-C', str(root), 'rev-parse', 'HEAD'],
                                capture_output=True, text=True, encoding='utf-8', check=True)
        return result.stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        return None


def strict_object(text):
    def invalid_constant(value):
        raise ValueError('Non-JSON numeric constant: ' + value)

    def unique_pairs(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise ValueError('Duplicate JSON key: ' + key)
            result[key] = value
        return result

    candidate = json.loads(text, parse_constant=invalid_constant, object_pairs_hook=unique_pairs)
    if not isinstance(candidate, dict):
        raise ValueError('Candidate must be a JSON object')
    return candidate


def project_result(output, returncode):
    """Project compatibility result.json; canonical shared evidence stays untouched."""
    summary = read_json(output / 'SUMMARY.json')
    attempts = summary['attempts']
    last = attempts[-1] if attempts else {}
    ready = (returncode == 0 and summary.get('success') is True
             and last.get('candidate_complete') is True
             and last.get('finish_reason') == 'stop' and last.get('sse_done') is True
             and last.get('failure') is None)
    candidate = None
    error = last.get('failure') or (None if ready else 'No complete stop/DONE candidate')
    if ready:
        try:
            content = Path(last['content_path']).resolve()
            if not content.is_relative_to(output.resolve()):
                raise ValueError('Candidate content is outside its evidence directory')
            candidate = strict_object(content.read_text(encoding='utf-8-sig'))
        except (OSError, ValueError, KeyError, TypeError) as exc:
            ready, error = False, str(exc)
    result = {**last, 'schema': 'civ6.shared-candidate-result/v1', 'success': ready,
              'candidate': candidate, 'adopted': None, 'error': error,
              'canonical_summary': 'SUMMARY.json', 'shared_cli_returncode': returncode}
    write_json(output / 'result.json', result)
    return 0 if ready else 1


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--task', required=True, type=Path)
    parser.add_argument('--source', action='append', required=True, type=Path)
    parser.add_argument('--output-dir', required=True, type=Path)
    parser.add_argument('--max-tokens', required=True, type=int)
    parser.add_argument('--timeout', type=float, help='Explicit shared read_seconds override; default comes from shared config')
    parser.add_argument('--config', type=Path, default=DEFAULT_CONFIG, help='Civ6 adapter manifest, not a second HTTP configuration')
    parser.add_argument('--task-id')
    parser.add_argument('--machine-id', default=os.environ.get('LOCAL_MODEL_MACHINE_ID'))
    parser.add_argument('--owner', default=os.environ.get('LOCAL_MODEL_OWNER'))
    parser.add_argument('--stop-file', type=Path)
    args = parser.parse_args(argv)
    try:
        if not 1 <= args.max_tokens <= 16000:
            raise ValueError('max-tokens must be 1..16000')
        if args.timeout is not None and (not math.isfinite(args.timeout) or not 0 < args.timeout <= 3600):
            raise ValueError('timeout must be finite, >0 and <=3600')
        output = args.output_dir.resolve()
        if output.exists():
            raise ValueError('Evidence directory already exists; use a new task directory')
        project = read_json(args.config)
        if project['schema'] != 'civ6.local-model-adapter/v1':
            raise ValueError('Expected Civ6 shared adapter manifest; old HTTP configs are historical only')
        shared = resolve_shared(project)
        canonical_path = shared / 'config/executor.json'
        canonical = canonical_path.read_bytes()
        config = copy.deepcopy(json.loads(canonical.decode('utf-8-sig')))
        system = project['prompting']['system_template']
        if not isinstance(system, str) or not system.strip():
            raise ValueError('Missing Civ6 system template')
        config['prompting']['system_template'] = system
        if args.timeout is not None:
            config.setdefault('timeouts', {})['read_seconds'] = args.timeout
        task = args.task.read_text(encoding='utf-8-sig')
        if not task.strip():
            raise ValueError('Task must be nonempty UTF-8 text')
        sources = '\n\n'.join('FILE ' + path.as_posix() + '\n' + path.read_text(encoding='utf-8-sig')
                               for path in sorted(set(args.source), key=lambda path: path.as_posix()))
        request = {'model': config['model'], 'max_tokens': args.max_tokens,
                   'messages': [{'role': 'system', 'content': system},
                                {'role': 'user', 'content': sources}, {'role': 'user', 'content': task}]}
        provenance = {'schema': 'civ6.local-model-adapter-provenance/v1',
                      'shared_repository': project['shared_repository']['url'],
                      'shared_commit': shared_revision(shared),
                      'canonical_config_sha256': hashlib.sha256(canonical).hexdigest(),
                      'canonical_caller_sha256': hashlib.sha256((shared / 'scripts/call.py').read_bytes()).hexdigest(),
                      'project_manifest_sha256': hashlib.sha256(args.config.read_bytes()).hexdigest(),
                      'overrides': {'prompting.system_template': system}, 'timeout_override': args.timeout,
                      'maintenance': 'Delegated to canonical call.py CLI client_preflight, before HTTP'}
        # The canonical CLI owns daily preflight, HTTP, SSE and retries.
        with tempfile.TemporaryDirectory(prefix='civ6-model-') as temporary:
            folder = Path(temporary)
            spec = folder / 'request.json'
            effective = folder / 'executor.json'
            write_json(spec, request)
            write_json(effective, config)
            command = [sys.executable, '-X', 'utf8', str(shared / 'scripts/call.py'),
                       str(spec), args.task_id or output.name, '--config', str(effective), '--output', str(output)]
            for flag, value in (('--machine-id', args.machine_id), ('--owner', args.owner), ('--stop-file', args.stop_file)):
                if value is not None:
                    command.extend([flag, str(value)])
            returned = subprocess.run(command, shell=False).returncode
        if returned not in (0, 1):
            # Preserve 75 / AI_REPAIR_REQUIRED for the owning AI to repair.
            return returned
        write_json(output / 'ADAPTER-PROVENANCE.json', provenance)
        return project_result(output, returned)
    except (OSError, ValueError, KeyError, TypeError) as exc:
        print('local_model.py: ' + str(exc), file=sys.stderr)
        return 1


if __name__ == '__main__':
    sys.exit(main())
