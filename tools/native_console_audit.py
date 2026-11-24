"""Record one Console call and audit its conservative host/game clock bounds.

This module has no game transport, action retry, clock synchronization, or process
control. The owner supplies the existing transport and independently verifies the
current game/parent. A quiet observation protocol needs this separate audit.
"""
from datetime import datetime, timezone
import hashlib
import json
import math
from pathlib import Path
import threading


def utc_now():
    return datetime.now(timezone.utc).isoformat()


def timestamp(value):
    parsed = datetime.fromisoformat(value)
    if parsed.tzinfo is None:
        raise ValueError('Timezone-aware UTC timestamps required')
    return parsed.timestamp()


def code_digest(code):
    return hashlib.sha256(code.encode('utf-8')).hexdigest()


def finite_number(value):
    if isinstance(value, bool):
        raise ValueError('Boolean is not a clock value')
    number = float(value)
    if not math.isfinite(number):
        raise ValueError('Finite clock value required')
    return number


def marker_rows(messages, marker):
    found = []
    for message in messages:
        if message.get('tag') != -1:
            continue
        for line in message['payload'].splitlines():
            fields = line.split(': ', 1)[-1].split('\t')
            if fields[0] == marker:
                found.append(fields[1:])
    return found


class QueryRecorder:
    """Exactly one delegate invocation, with exclusive attempt/return records."""

    def __init__(self, directory, delegate, metadata):
        self.directory = Path(directory)
        self.directory.mkdir(exist_ok=False)
        self.delegate = delegate
        self.metadata = metadata
        self.sequence = 0
        self.in_flight = False
        self._lock = threading.Lock()

    def _write(self, name, value):
        with (self.directory / name).open('x', encoding='utf-8', newline='\n') as output:
            json.dump(value, output, ensure_ascii=False, indent=2, allow_nan=False)

    def __call__(self, context, code):
        if not self._lock.acquire(blocking=False):
            raise RuntimeError('Concurrent or nested Console calls are not admitted')
        self.in_flight = True
        try:
            return self._call(context, code)
        finally:
            self.in_flight = False
            self._lock.release()

    def _call(self, context, code):
        if not isinstance(context, str) or not context or not isinstance(code, str) or not code:
            raise ValueError('Explicit nonempty context and authored code required')
        metadata = self.metadata()
        if not isinstance(metadata, dict) or any(k in metadata for k in ('utc', 'context', 'authored_code', 'code_sha256', 'sequence')):
            raise ValueError('Invalid owner metadata')
        self.sequence += 1
        sequence = self.sequence
        attempt = dict(metadata, utc=utc_now(), sequence=sequence,
                       context=context, authored_code=code, code_sha256=code_digest(code),
                       delegate_invocations=1, action_retries=0)
        self._write(f'{sequence:06}-attempt.json', attempt)
        try:
            messages = self.delegate(context, code)
        except BaseException as error:
            self._write(f'{sequence:06}-returned.json', dict(
                utc=utc_now(), sequence=sequence, exception_type=type(error).__name__,
                exception=repr(error), action_retries=0))
            raise
        self._write(f'{sequence:06}-returned.json', dict(
            utc=utc_now(), sequence=sequence, messages=messages, action_retries=0))
        return messages


def intersects_window(start, end, anchor, offset_low, offset_high):
    start, end, anchor, offset_low, offset_high = map(
        finite_number, (start, end, anchor, offset_low, offset_high))
    if start > end or offset_low > offset_high:
        raise ValueError('Ordered intervals required')
    return start + offset_low <= anchor + 10 and end + offset_high >= anchor


def audit_transactions(attempts, wires, anchors, calibrations, *, owner,
                       source_version, arm_utc, endpoints, quantum_seconds=.002):
    """Finite audit of complete owner records, raw wire, and actual clock reads.

    Inputs must already cover the entire cold-launch to saved-exit interval.
    This function never filters samples or infers action success from a reply.
    """
    quantum_seconds = finite_number(quantum_seconds)
    if quantum_seconds < 0:
        raise ValueError('Nonnegative clock uncertainty required')
    if len(anchors) != 5 or len(calibrations) < 7:
        raise ValueError('Five windows and at least seven actual clock reads required')
    ordered = sorted((int(k), finite_number(v)) for k, v in anchors.items())
    if len(set(k for k, _ in ordered)) != 5 or any(
            k2 != k1 + 1 or v2 <= v1 for (k1, v1), (k2, v2) in zip(ordered, ordered[1:])):
        raise ValueError('Consecutive ordered actual anchors required')
    brackets = []
    for value in calibrations:
        start, end = timestamp(value['host_start']), timestamp(value['host_end'])
        now = finite_number(value['actual_game_now'])
        if start > end:
            raise ValueError('Clock read returned before it started')
        brackets.append(dict(value, offset_low=now-end-quantum_seconds,
                             offset_high=now-start+quantum_seconds))
    consistent = max(x['offset_low'] for x in brackets) <= min(x['offset_high'] for x in brackets)
    low = min(x['offset_low'] for x in brackets)
    high = max(x['offset_high'] for x in brackets)
    wire_ids = [w['name'] for w in wires]
    if len(set(wire_ids)) != len(wire_ids):
        raise ValueError('Duplicate raw wire receipt name')
    matched = set()
    unknown = []
    transactions = []
    exceptions = []
    seen_sequences = set()
    for item in attempts:
        attempt, returned = item['attempt'], item['returned']
        seq = attempt['sequence']
        if type(seq) is not int or seq in seen_sequences or seq != returned['sequence']:
            raise ValueError('Unique matching attempt/return sequence required')
        seen_sequences.add(seq)
        if attempt['owner'] != owner or attempt['source_version'] != source_version:
            raise ValueError('Current source and exact game owner required')
        start, end = timestamp(attempt['utc']), timestamp(returned['utc'])
        if start > end or attempt['code_sha256'] != code_digest(attempt['authored_code']):
            raise ValueError('Invalid authored request or host interval')
        if attempt['delegate_invocations'] != 1 or attempt['action_retries'] != 0 or returned['action_retries'] != 0:
            raise ValueError('One transport call and zero action retries required')
        candidates = [w for w in wires if start-quantum_seconds <= timestamp(w['utc']) <= end+quantum_seconds
                      and w['context'] == attempt['context']
                      and code_digest(w['authored_code']) == attempt['code_sha256']]
        if len(candidates) != 1 or candidates[0]['name'] in matched:
            unknown.append(dict(sequence=seq, wire_matches=len(candidates)))
            continue
        wire = candidates[0]
        matched.add(wire['name'])
        overlaps = [turn for turn, anchor in ordered if intersects_window(start, end, anchor, low, high)]
        row = dict(sequence=seq, wire=wire['name'], wire_sha256=wire['sha256'],
                   context=attempt['context'], role=attempt['role'],
                   code_sha256=attempt['code_sha256'], host_start=start,
                   host_returned_record=end, window_overlaps=overlaps)
        transactions.append(row)
        if 'exception' in returned:
            exceptions.append(dict(sequence=seq, exception=returned['exception']))
    if sorted(seen_sequences) != list(range(1, len(attempts)+1)):
        raise ValueError('Complete contiguous recording sequence required')
    unmatched = [name for name in wire_ids if name not in matched]
    overlaps = [row for row in transactions if row['window_overlaps']]
    endpoints_before_arm = bool(endpoints) and all(
        endpoint['owner'] == owner and endpoint['no_CMD_sent'] is True
        and timestamp(endpoint['utc']) < timestamp(arm_utc) for endpoint in endpoints)
    qualified = bool(attempts) and consistent and not unknown and not unmatched and not overlaps and endpoints_before_arm
    return dict(quiet_observer_qualified=qualified,
                status='QUALIFIED_ZERO_RECORDED_TRANSACTION_OVERLAP' if qualified else 'NOT_QUALIFIED',
                anchors=dict(ordered), clock_calibrations=brackets,
                constant_offset_brackets_consistent=consistent,
                conservative_observed_game_minus_host_offset_union=[low, high],
                actual_query_attempts=len(attempts), actual_matched_wire_receipts=len(matched),
                unknown_matches=unknown, unmatched_wire_receipts=unmatched,
                overlap_transactions=overlaps, transactions=transactions,
                returned_exceptions=exceptions, LSQ_only_endpoint_records=len(endpoints),
                all_LSQ_only_completed_before_armed=endpoints_before_arm,
                limits='Finite observed host/game clock brackets with conservative full-call enclosure; '
                       'not exact CMD CPU intervals, action completion proof, or a root cause claim.')
