"""File reservations separating model work from formal game measurements.

No process/network actions or stale-record cleanup. A failed admitted operation
retains its reservation until its owner reconciles what actually happened.
"""
from collections.abc import Mapping
from contextlib import contextmanager
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import re
import uuid


class AdmissionError(RuntimeError):
    pass


MODEL = 'MODEL_ACTIVITY'
FORMAL = 'FORMAL_PERFORMANCE'


def _paths(root):
    root = Path(root).resolve()
    cache = root / '.local-model'
    return root, cache / 'p6-formal-performance-active.json', cache / 'model-activity'


def _present(path):
    return path.exists() or path.is_symlink()


def _record(metadata, nonce, role):
    if metadata is not None and not isinstance(metadata, Mapping):
        raise AdmissionError('Admission metadata must be a mapping')
    return {**dict(metadata or {}), 'nonce': nonce, 'role': role,
            'pid': os.getpid(), 'utc': datetime.now(timezone.utc).isoformat()}


def _write(path, data):
    # Serialize before creating the exclusive file, including caller metadata.
    encoded = json.dumps(data, ensure_ascii=False, allow_nan=False, indent=2)
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        with path.open('x', encoding='utf-8', newline='\n') as stream:
            stream.write(encoded + '\n')
    except OSError as exc:
        raise AdmissionError('Cannot create admission reservation: ' + str(exc)) from exc


def _handle(root, path, nonce, role):
    return {'root': str(root), 'path': str(path), 'nonce': nonce, 'role': role}


def _release(handle, role):
    if (not isinstance(handle, Mapping) or handle.get('role') != role
            or not isinstance(handle.get('nonce'), str)
            or re.fullmatch('[0-9a-f]{32}', handle['nonce']) is None
            or not isinstance(handle.get('root'), str)
            or not isinstance(handle.get('path'), str)):
        raise AdmissionError('Invalid admission handle')
    root, formal, models = _paths(handle['root'])
    expected = formal if role == FORMAL else models / (handle['nonce'] + '.json')
    path = Path(handle['path'])
    if path.is_symlink() or path.resolve() != expected.resolve() or not path.resolve().is_relative_to(root):
        raise AdmissionError('Admission path does not match its owned location')
    try:
        data = json.loads(path.read_text(encoding='utf-8'))
        if not isinstance(data, dict) or data.get('nonce') != handle['nonce'] or data.get('role') != role:
            raise AdmissionError('Reservation changed; preserve it for reconciliation')
        path.unlink()
    except (OSError, ValueError) as exc:
        raise AdmissionError('Cannot release owned reservation: ' + str(exc)) from exc


def _model_leases(root):
    _, _, models = _paths(root)
    try:
        if not _present(models):
            return []
        if not models.is_dir() or models.is_symlink():
            raise AdmissionError('Model activity directory is unknown')
        # Unknown entries also block measurement; never guess that they are stale.
        return list(models.iterdir())
    except OSError as exc:
        raise AdmissionError('Cannot inspect model reservations') from exc


def assert_no_model_activity(root):
    if _model_leases(root):
        raise AdmissionError('Model work is active or unresolved')


@contextmanager
def model_activity(root, metadata=None):
    root, formal, models = _paths(root)
    if _present(formal):
        raise AdmissionError('Formal performance is active or unresolved')
    nonce = uuid.uuid4().hex
    path = models / (nonce + '.json')
    _write(path, _record(metadata, nonce, MODEL))
    handle = _handle(root, path, nonce, MODEL)
    if _present(formal):
        release_model(handle)
        raise AdmissionError('Formal performance appeared before model admission')
    try:
        yield handle
    except BaseException:
        # Child dispatch may be unresolved. Explicit reconciliation is required.
        raise
    else:
        release_model(handle)


def release_model(handle):
    _release(handle, MODEL)


def begin_formal(root, metadata=None):
    root, formal, _ = _paths(root)
    nonce = uuid.uuid4().hex
    _write(formal, _record(metadata, nonce, FORMAL))
    handle = _handle(root, formal, nonce, FORMAL)
    try:
        assert_no_model_activity(root)
    except BaseException:
        finish_formal(handle)
        raise
    return handle


def finish_formal(handle):
    """Call only after the owner proves the capture complete or reconciled."""
    _release(handle, FORMAL)
