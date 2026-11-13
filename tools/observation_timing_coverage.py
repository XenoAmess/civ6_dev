"""Reject timing pauses that could intersect any required observation window."""
from collections.abc import Mapping, Sequence
import math


def _number(value):
    if type(value) not in (int, float) or not math.isfinite(value) or value < 0:
        raise ValueError('Expected finite nonnegative clock')
    return value


def validate_timing_phases(phases, keys, clock_bounds, windows, capture_bounds, closing_start):
    """Audit conservative pause envelopes using the complete calibration bounds.

    Each context must have one pause/resume pair before every recorded END,
    including the initialization turn. Anchors and writes stay enabled throughout.
    This complements complete sample accounting; it never repairs missing rows.
    """
    def sequence(v):
        return isinstance(v, Sequence) and not isinstance(v, (str, bytes, bytearray))
    if (not sequence(keys) or not keys or len(keys) > 80
            or any(type(k) is not str or not k for k in keys) or len(set(keys)) != len(keys)):
        raise ValueError('Expected unique context keys')
    if not sequence(windows) or not windows:
        raise ValueError('Expected complete observation windows')
    turns = []
    for w in windows:
        if not isinstance(w, Mapping) or type(w.get('turn')) is not int:
            raise ValueError('Malformed observation window')
        a, z = _number(w.get('start_ui')), _number(w.get('end_ui'))
        if w['turn'] < 1 or z - a != 10:
            raise ValueError('Expected fixed ten-second window')
        turns.append(w['turn'])
    if turns != list(range(turns[0], turns[-1] + 1)):
        raise ValueError('Expected consecutive windows')
    closing_start = _number(closing_start)
    if not sequence(capture_bounds) or len(capture_bounds) != 2:
        raise ValueError('Expected capture bounds')
    cap_start, cap_stop = map(_number, capture_bounds)
    if (cap_stop < cap_start or cap_start > windows[0]['start_ui']
            or closing_start < windows[-1]['end_ui'] or cap_stop < closing_start):
        raise ValueError('Capture does not cover observation windows')
    if not isinstance(clock_bounds, Mapping) or set(clock_bounds) != set(keys):
        raise ValueError('Missing context clock calibration')
    bounds = {}
    for key in keys:
        b = clock_bounds[key]
        if not isinstance(b, Mapping):
            raise ValueError('Malformed calibration bounds')
        lo, hi = b.get('lower_seconds'), b.get('upper_seconds')
        if (type(lo) not in (int, float) or type(hi) not in (int, float)
                or not math.isfinite(lo) or not math.isfinite(hi) or lo > hi):
            raise ValueError('Invalid clock offset interval')
        bounds[key] = lo, hi
    if not sequence(phases) or len(phases) != len(keys) * (len(turns) + 1) * 2:
        raise ValueError('Incomplete timing phase evidence')
    by_key = {key: [] for key in keys}
    fields = {'key', 'turn', 'timing_enabled', 'local_before', 'local_after',
              'recording', 'subscribed', 'retired'}
    for p in phases:
        if (not isinstance(p, Mapping) or set(p) != fields or type(p['key']) is not str or p['key'] not in by_key
                or type(p['turn']) is not int or type(p['timing_enabled']) is not bool
                or p['recording'] is not True or p['subscribed'] is not True or p['retired'] is not False):
            raise ValueError('Unqualified timing phase')
        a, z = _number(p['local_before']), _number(p['local_after'])
        if z < a:
            raise ValueError('Reversed phase clocks')
        by_key[p['key']].append(p)
    expected = [(turn, flag) for turn in [turns[0] - 1, *turns] for flag in (False, True)]
    pauses = []
    for key, events in by_key.items():
        if [(p['turn'], p['timing_enabled']) for p in events] != expected:
            raise ValueError('Missing, duplicate, or unordered timing transition')
        if any(b['local_before'] < a['local_after'] for a, b in zip(events, events[1:])):
            raise ValueError('Overlapping or reversed phase transitions')
        offset_lo, offset_hi = bounds[key]
        for off, on in zip(events[::2], events[1::2]):
            # Include the whole possible disable-to-enable interval. Midpoint
            # alignment alone must never hide a possible window overlap.
            a, z = off['local_before'] - offset_hi, on['local_after'] - offset_lo
            if not math.isfinite(a) or not math.isfinite(z) or a < cap_start or z > cap_stop:
                raise ValueError('Pause lies outside capture bounds')
            if any(a < w['end_ui'] and z > w['start_ui'] for w in windows):
                raise ValueError('Timing pause may overlap a required observation window')
            current = next((w for w in windows if w['turn'] == off['turn']), None)
            if current is not None and a < current['end_ui']:
                raise ValueError('Timing paused before its current window closed')
            following = next((w for w in windows if w['turn'] == off['turn'] + 1), None)
            next_start = following['start_ui'] if following is not None else closing_start
            if z > next_start:
                raise ValueError('Context not resumed before following activation')
            pauses.append({'key': key, 'turn': off['turn'], 'earliest_ui': a, 'latest_ui': z})
    return {'contexts': len(keys), 'phase_rows': len(phases), 'pause_pairs': len(pauses),
            'coverage_ok': True, 'conservative_pause_envelopes': pauses,
            'limits': 'Timing coverage only; full sample accounting, native writes, and budgets require the capture analyzer.'}
