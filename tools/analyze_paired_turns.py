import collections.abc, statistics, math

def _finite(value):
    if type(value) not in (int,float):return False
    try:return math.isfinite(value)
    except (OverflowError,ValueError):return False


def validate_capture_mode(capture, expected_source_version, require_ordinary, initial_turn=None):
    if type(expected_source_version) is not int or expected_source_version not in (67, 140, 141, 142):
        raise ValueError('expected_source_version must be int 67,140 or141')
    if type(require_ordinary) is not bool:
        raise ValueError('require_ordinary must be bool')
    if require_ordinary and expected_source_version not in (140,141,142):
        raise ValueError('require_ordinary requires expected_source_version 140 or141')
    if not isinstance(capture, collections.abc.Mapping):
        raise ValueError('capture must be a mapping')
    if type(capture.get('source_version')) is not int or capture.get('source_version') != expected_source_version:
        raise ValueError('source_version mismatch')
    if initial_turn is None:
        if capture.get('source') == 'baiqi142-pressure-paired-v1' or 'initial_turn' in capture:
            raise ValueError('Pressure capture requires pressure analyzer')
    else:
        if (expected_source_version != 142 or require_ordinary is not True
                or capture.get('source') != 'baiqi142-pressure-paired-v1'
                or type(capture.get('initial_turn')) is not int or capture['initial_turn'] != initial_turn):
            raise ValueError('Pressure capture metadata mismatch')
    if require_ordinary:
        if capture.get('end_mode') != 'ORDINARY_CALLBACK':
            raise ValueError('end_mode must be ORDINARY_CALLBACK')
        if capture.get('forced') is not False:
            raise ValueError('forced must be False')
        if capture.get('phase') != 'COMPLETE':
            raise ValueError('phase must be COMPLETE')
        req = capture.get('requested_turns')
        first = 85 if initial_turn is None else initial_turn
        if not isinstance(req, list) or len(req) != 5 or any(type(t) is not int or t != first+i for i, t in enumerate(req)):
            raise ValueError('requested_turns do not match calendar')
    return True


def _analyze_core(pairs, fixture_sha256, expected_source_version, require_ordinary, initial_turn):
    first = 85 if initial_turn is None else initial_turn
    if not isinstance(pairs, collections.abc.Sequence) or isinstance(pairs, (str, bytes, bytearray, collections.abc.Mapping)):
        raise ValueError('pairs must be a sequence of 5 mappings')
    if len(pairs) != 5:
        raise ValueError('pairs must contain exactly 5 items')
    if not isinstance(fixture_sha256, str) or len(fixture_sha256) != 64 or not all(c in '0123456789abcdef' for c in fixture_sha256):
        raise ValueError('fixture_sha256 must be 64 lowercase hex chars')

    all_records = []
    pair_medians = []
    seen_run_ids = set()

    for idx, pair in enumerate(pairs):
        if not isinstance(pair, collections.abc.Mapping):
            raise ValueError('pair must be a mapping')
        if type(pair.get('pair')) is not int or pair.get('pair') != idx + 1:
            raise ValueError('pair index mismatch')
        order = pair.get('order')
        if not isinstance(order, collections.abc.Sequence) or isinstance(order, (str, bytes, bytearray)) or len(order) != 2:
            raise ValueError('order must be a sequence of 2 strings')
        if order[0] not in ('enabled', 'control') or order[1] not in ('enabled', 'control') or order[0] == order[1]:
            raise ValueError('order must be [enabled, control] or [control, enabled]')
        expected_order = ['enabled', 'control'] if (idx + 1) % 2 == 1 else ['control', 'enabled']
        if list(order) != expected_order:
            raise ValueError('order does not match alternating protocol')

        for variant in ('enabled', 'control'):
            capture = pair.get(variant)
            if not isinstance(capture, collections.abc.Mapping):
                raise ValueError('capture must be a mapping')
            if capture.get('variant') != variant:
                raise ValueError('variant mismatch')
            run_id = capture.get('run_id')
            if not isinstance(run_id, str) or not run_id:
                raise ValueError('run_id must be non-empty string')
            if run_id in seen_run_ids:
                raise ValueError('run_id must be unique across all 10 runs')
            seen_run_ids.add(run_id)
            if capture.get('fixture_sha256') != fixture_sha256:
                raise ValueError('fixture_sha256 mismatch')
            validate_capture_mode(capture,expected_source_version,require_ordinary,initial_turn)
            if any(type(capture.get(k)) is not int or capture.get(k)!=0 for k in ('errors','refused')):
                raise ValueError('errors and refused must be 0')
            records = capture.get('records')
            if not isinstance(records, collections.abc.Sequence) or isinstance(records, (str, bytes, bytearray)) or len(records) != 5:
                raise ValueError('records must be a sequence of 5 items')

            for i, rec in enumerate(records):
                if not isinstance(rec, collections.abc.Mapping):
                    raise ValueError('record must be a mapping')
                ft = rec.get('from_turn')
                tt = rec.get('to_turn')
                pid = rec.get('pid')
                started = rec.get('started')
                ended = rec.get('ended')
                seconds = rec.get('seconds')

                if not isinstance(ft, int) or isinstance(ft, bool) or ft != first + i:
                    raise ValueError('from_turn mismatch')
                if not isinstance(tt, int) or isinstance(tt, bool) or tt != first + 1 + i:
                    raise ValueError('to_turn mismatch')
                if not isinstance(pid, int) or isinstance(pid, bool) or pid != 0:
                    raise ValueError('pid must be 0')
                if not isinstance(started, (int, float)) or isinstance(started, bool) or not _finite(started) or started < 0:
                    raise ValueError('started invalid')
                if not isinstance(ended, (int, float)) or isinstance(ended, bool) or not _finite(ended) or ended < started:
                    raise ValueError('ended invalid')
                if not isinstance(seconds, (int, float)) or isinstance(seconds, bool) or not _finite(seconds) or seconds < 0:
                    raise ValueError('seconds invalid')
                if abs(seconds - (ended - started)) > 1e-6:
                    raise ValueError('seconds does not match ended-started')

                if i > 0:
                    prev = records[i - 1]
                    prev_ended = prev.get('ended')
                    if not isinstance(prev_ended, (int, float)) or isinstance(prev_ended, bool):
                        raise ValueError('previous ended invalid')
                    if started < prev_ended + 10:
                        raise ValueError('interval violation: started < previous ended + 10')

                all_records.append({
                    'pair': idx + 1,
                    'turn': first+i+1,
                    'variant': variant,
                    'seconds': seconds
                })

    # Match pairs by turn index (0..4) within each pair
    matched_deltas = []
    for p_idx in range(5):
        pair_records = [r for r in all_records if r['pair'] == p_idx + 1]
        enabled_secs = [r['seconds'] for r in pair_records if r['variant'] == 'enabled']
        control_secs = [r['seconds'] for r in pair_records if r['variant'] == 'control']
        if len(enabled_secs) != 5 or len(control_secs) != 5:
            raise ValueError('missing records for pair')
        for i in range(5):
            e_s = enabled_secs[i]
            c_s = control_secs[i]
            delta = e_s - c_s
            ratio = None if c_s == 0 else (delta / c_s) * 100.0
            delta_ms=delta*1000.0
            if not _finite(delta_ms) or (ratio is not None and not _finite(ratio)):
                raise ValueError('Derived timing metric overflow')
            matched_deltas.append({
                'pair': p_idx + 1,
                'turn': first+i+1,
                'enabled_seconds': e_s,
                'control_seconds': c_s,
                'delta_ms': delta_ms,
                'ratio_percent': ratio
            })

    # Per-pair medians
    for p_idx in range(5):
        p_deltas = [d['delta_ms'] for d in matched_deltas if d['pair'] == p_idx + 1]
        p_ratios = [d['ratio_percent'] for d in matched_deltas if d['pair'] == p_idx + 1 and d['ratio_percent'] is not None]
        med_delta = statistics.median(p_deltas)
        med_ratio = statistics.median(p_ratios) if len(p_ratios)==5 else None
        pair_medians.append({
            'pair': p_idx + 1,
            'median_delta_ms': med_delta,
            'median_ratio_percent': med_ratio
        })

    # Global medians
    all_deltas = [d['delta_ms'] for d in matched_deltas]
    all_ratios = [d['ratio_percent'] for d in matched_deltas if d['ratio_percent'] is not None]
    top_median_delta = statistics.median(all_deltas)
    top_median_ratio = statistics.median(all_ratios) if len(all_ratios)==25 else None
    ratio_known = len(all_ratios) == 25
    budget_ok = ratio_known and top_median_delta <= 500 and (top_median_ratio is not None and top_median_ratio <= 10)

    result = {
        'matched_rows': matched_deltas,
        'pair_medians': pair_medians,
        'median_delta_ms': top_median_delta,
        'median_ratio_percent': top_median_ratio,
        'ratio_known': ratio_known,
        'observed_b_delta_budget_ok': budget_ok,
        'limits': ['Input arithmetic only; physical execution/order, Native AI, operator input, clock precision and assets require separate evidence.']
    }
    if require_ordinary or expected_source_version!=67:
        result.update(source_version=expected_source_version,ordinary_required=require_ordinary)
    return result


def analyze_pairs(pairs, fixture_sha256, *, expected_source_version=67, require_ordinary=False):
    return _analyze_core(pairs, fixture_sha256, expected_source_version, require_ordinary, None)


def analyze_pressure_pairs(pairs, fixture_sha256, *, initial_turn):
    """Analyze actual pressure-calendar labels without rewriting capture data."""
    if type(initial_turn) is not int or not 0 <= initial_turn <= 2147483641:
        raise ValueError('Invalid pressure initial_turn')
    result = _analyze_core(pairs, fixture_sha256, 142, True, initial_turn)

    def distribution(values, threshold, key):
        if any(v is None for v in values):
            return dict(p50=None,p95=None,max=None,**{key:None})
        ordered = sorted(values)
        return dict(p50=statistics.median(ordered),p95=ordered[math.ceil(.95*len(ordered))-1],
                    max=ordered[-1],**{key:sum(v>threshold for v in values)})

    result.update(source='baiqi142-pressure-paired-v1',initial_turn=initial_turn,
                  pressure_distributions={
                      'delta_ms':distribution([r['delta_ms'] for r in result['matched_rows']],500,'over_500_count'),
                      'ratio_percent':distribution([r['ratio_percent'] for r in result['matched_rows']],10,'over_10_count')})
    return result
