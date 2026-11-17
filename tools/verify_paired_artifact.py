"""Read-only qualification of ordinary-END and explicitly pinned pressure pairs."""
from pathlib import Path
import hashlib
import json
import xml.etree.ElementTree as ET
import zipfile

from tools.build_mod import contained, digest, manifest_files
from tools.build_static_control import ROOT, clock_prelude
from tools.diagnostic_version_render import render_helper
from tools.static_control_source import edits, transform


def verify_pair(prepared: Path, source: Path, variant: str, *,
                pressure_initial_turn: int | None = None) -> dict:
    """Check files and canonical transformations; never build, install or run Lua.

    The caller still owns lifecycle, fresh process/offline/admission checks and
    protecting saves. Successful qualification is not native B_delta evidence.
    """
    prepared, source = Path(prepared), Path(source)
    if variant not in ('enabled', 'control'):
        raise ValueError('Invalid paired variant')
    if pressure_initial_turn is not None and (type(pressure_initial_turn) is not int
            or not 0 <= pressure_initial_turn <= 2147483641):
        raise ValueError('Invalid expected pressure initial turn')
    meta = json.loads((prepared / 'static-control-build.json').read_text(encoding='utf-8'))
    version = ET.fromstring((source / 'Baiqi.modinfo').read_bytes()).get('version')
    if version not in ('152', '153','154','155','156','157','158','159','160','161'):
        raise ValueError('Expected actual source152/153')
    version = int(version)
    if not isinstance(meta, dict) or type(meta.get('source_version')) is not int or meta['source_version'] != version:
        raise ValueError('Expected matching source152/153 metadata')
    mode = (f'baiqi{version}-paired-{variant}-c3-normal-end' if pressure_initial_turn is None
            else f'baiqi{version}-pressure-paired-{variant}-v1')
    if meta.get('variant') != variant or meta.get('mode') != mode:
        raise ValueError('Variant or mode mismatch')
    if pressure_initial_turn is None:
        if any(k in meta for k in ('source', 'initial_turn', 'paired_end_turns', 'paired_activation_turns')):
            raise ValueError('Unexpected pressure calendar in ordinary pair')
    else:
        def exact_turns(value, first):
            return (type(value) is list and len(value) == 5
                    and all(type(v) is int and v == expected
                            for v, expected in zip(value, range(first, first + 5))))
        if (meta.get('source') != f'baiqi{version}-pressure-paired-v1'
                or type(meta.get('initial_turn')) is not int or meta['initial_turn'] != pressure_initial_turn
                or not exact_turns(meta.get('paired_end_turns'), pressure_initial_turn)
                or not exact_turns(meta.get('paired_activation_turns'), pressure_initial_turn + 1)):
            raise ValueError('Pressure source or frozen calendar mismatch')
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
        expected_changed |= set(edits(version))
    changed = {n for n in names if source_hashes[n] != target_hashes[n]}
    declared = meta.get('changed_files')
    if not isinstance(declared, list) or len(declared) != len(expected_changed) or set(declared) != expected_changed or changed != expected_changed:
        raise ValueError('Changed file set mismatch')
    prefix = clock_prelude(normal_end_bridge=True, source_version=version,
                           pressure_initial_turn=pressure_initial_turn)
    bridge = render_helper((ROOT / 'tools/lua/benchmark_end_bridge.lua').read_text(encoding='utf-8'),
                           'benchmark_end_bridge', version)
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
        expected = transform(raw, n, version)[0] if variant == 'control' else raw
        if n == 'UI/BaiqiExecutor.lua':
            expected = prefix + expected
            for old, new in aliases.items():
                if expected.count(old) != 1:
                    raise ValueError('Unknown activation alias')
                expected = expected.replace(old, new, 1)
        if contained(target, n).read_bytes() != expected.encode('utf-8'):
            raise ValueError('Prepared source differs from canonical paired transformation: ' + n)
    suffix = '' if pressure_initial_turn is None else f'-pressure-{pressure_initial_turn}'
    archive = prepared / f'Baiqi-paired{version}-{variant}-normal-end{suffix}.zip'
    if digest(archive) != meta.get('archive_sha256'):
        raise ValueError('Archive hash mismatch')
    with zipfile.ZipFile(archive) as z:
        expected_names = {'Baiqi/' + n for n in names}
        if len(z.namelist()) != len(expected_names) or set(z.namelist()) != expected_names:
            raise ValueError('Archive inventory mismatch')
        if any(z.read('Baiqi/' + n) != contained(target, n).read_bytes() for n in names):
            raise ValueError('Archive content mismatch')
    return meta
