"""Read-only qualification of held source152 ordinary-END paired packages."""
from pathlib import Path
import hashlib
import json
import xml.etree.ElementTree as ET
import zipfile

from tools.build_mod import contained, digest, manifest_files
from tools.build_static_control import ROOT, clock_prelude
from tools.diagnostic_version_render import render_helper
from tools.static_control_source import edits, transform


def verify_pair(prepared: Path, source: Path, variant: str) -> dict:
    """Check files and canonical transformations; never build, install or run Lua.

    The caller still owns lifecycle, fresh process/offline/admission checks and
    protecting saves. Successful qualification is not native B_delta evidence.
    """
    prepared, source = Path(prepared), Path(source)
    if variant not in ('enabled', 'control'):
        raise ValueError('Invalid paired variant')
    meta = json.loads((prepared / 'static-control-build.json').read_text(encoding='utf-8'))
    if not isinstance(meta, dict) or type(meta.get('source_version')) is not int or meta['source_version'] != 152:
        raise ValueError('Expected source152 metadata')
    if ET.fromstring((source / 'Baiqi.modinfo').read_bytes()).get('version') != '152':
        raise ValueError('Expected actual source152')
    if meta.get('variant') != variant or meta.get('mode') != f'baiqi152-paired-{variant}-c3-normal-end':
        raise ValueError('Variant or mode mismatch')
    if any(meta.get(k) is not True for k in ('paired_clock', 'normal_end_bridge', 'native_activation_inline_stop', 'lua51_compiled')):
        raise ValueError('Ordinary END bridge flags mismatch')
    names = manifest_files(source)
    target = prepared / 'Baiqi'
    if len(names) != 119 or meta.get('files') != 119 or manifest_files(target) != names:
        raise ValueError('Expected matching119-file manifests')
    source_hashes = {n: digest(contained(source, n)) for n in names}
    target_hashes = {n: digest(contained(target, n)) for n in names}
    if meta.get('source_hashes') != source_hashes or meta.get('control_hashes') != target_hashes:
        raise ValueError('Source or prepared hash mismatch')
    expected_changed = {'UI/BaiqiExecutor.lua'}
    if variant == 'control':
        expected_changed |= set(edits(152))
    changed = {n for n in names if source_hashes[n] != target_hashes[n]}
    declared = meta.get('changed_files')
    if not isinstance(declared, list) or len(declared) != len(expected_changed) or set(declared) != expected_changed or changed != expected_changed:
        raise ValueError('Changed file set mismatch')
    prefix = clock_prelude(normal_end_bridge=True, source_version=152)
    bridge = render_helper((ROOT / 'tools/lua/benchmark_end_bridge.lua').read_text(encoding='utf-8'),
                           'benchmark_end_bridge', 152)
    sha = lambda s: hashlib.sha256(s.encode('utf-8')).hexdigest()
    if meta.get('clock_prefix_sha256') != sha(prefix) or meta.get('rendered_end_bridge_sha256') != sha(bridge):
        raise ValueError('Current clock or bridge hash mismatch')
    aliases = {
        'Events.PlayerTurnActivated.Add(Activate)':
            'local P6PairActivation=P6PairClock:WrapActivation(Activate)\nEvents.PlayerTurnActivated.Add(P6PairActivation)',
        'Events.PlayerTurnActivated.Remove(Activate)': 'Events.PlayerTurnActivated.Remove(P6PairActivation)',
    }
    for n in expected_changed:
        raw = contained(source, n).read_text(encoding='utf-8-sig')
        expected = transform(raw, n, 152)[0] if variant == 'control' else raw
        if n == 'UI/BaiqiExecutor.lua':
            expected = prefix + expected
            for old, new in aliases.items():
                if expected.count(old) != 1:
                    raise ValueError('Unknown activation alias')
                expected = expected.replace(old, new, 1)
        if contained(target, n).read_bytes() != expected.encode('utf-8'):
            raise ValueError('Prepared source differs from canonical paired transformation: ' + n)
    archive = prepared / f'Baiqi-paired152-{variant}-normal-end.zip'
    if digest(archive) != meta.get('archive_sha256'):
        raise ValueError('Archive hash mismatch')
    with zipfile.ZipFile(archive) as z:
        expected_names = {'Baiqi/' + n for n in names}
        if len(z.namelist()) != len(expected_names) or set(z.namelist()) != expected_names:
            raise ValueError('Archive inventory mismatch')
        if any(z.read('Baiqi/' + n) != contained(target, n).read_bytes() for n in names):
            raise ValueError('Archive content mismatch')
    return meta
