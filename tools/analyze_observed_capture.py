"""Validate complete diagnostic rows before calculating observed budgets.

Clock precision, source coverage and a matched control are separate evidence.
"""
from collections.abc import Mapping,Sequence
import math
import re
from tools.clock_offsets import intersect_offsets
from tools.profile_intervals import union_seconds

ERROR_FIELDS=(1,2,3,4,5,6,7,9,10,11,12)


def _sequence(value):
    return isinstance(value,Sequence) and not isinstance(value,(str,bytes,bytearray,Mapping))


def _integer(value):
    if not isinstance(value,str) or not re.fullmatch(r'0|[1-9][0-9]*',value):
        raise ValueError('Expected exported nonnegative integer string')
    return int(value)


def _number(value,*,exported=False):
    if exported:
        if not isinstance(value,str) or not value or value!=value.strip():
            raise ValueError('Expected exported numeric string')
    elif isinstance(value,bool) or not isinstance(value,(int,float)):
        raise ValueError('Expected numeric clock')
    try:
        result=float(value)
    except (ValueError,TypeError,OverflowError) as error:
        raise ValueError('Unrepresentable clock') from error
    if not math.isfinite(result) or result<0:
        raise ValueError('Clock must be finite and nonnegative')
    return result


def analyze_capture(rows,brackets,expected_keys,capture_bounds,turns=(86,87,88,89,90),closing_turn=91,pid=0):
    if not _sequence(expected_keys) or not expected_keys or len(expected_keys)>80:
        raise ValueError('Expected explicit context keys')
    if any(not isinstance(k,str) or not k for k in expected_keys) or len(set(expected_keys))!=len(expected_keys):
        raise ValueError('Context keys must be unique strings')
    if not _sequence(turns) or not turns or any(type(t) is not int or t<0 for t in turns):
        raise ValueError('Expected ordered integer turns')
    if list(turns)!=list(range(turns[0],turns[-1]+1)) or type(closing_turn) is not int or closing_turn!=turns[-1]+1 or type(pid) is not int or pid<0:
        raise ValueError('Expected consecutive turns and following closure')
    if not _sequence(capture_bounds) or len(capture_bounds)!=2:
        raise ValueError('Expected UI capture bounds')
    cap_start,cap_stop=(_number(x) for x in capture_bounds)
    if cap_stop<cap_start:raise ValueError('Capture bounds reversed')
    if not _sequence(rows):raise ValueError('Expected exported row array')
    keys=set(expected_keys)
    meta={}
    samples=[]
    sample_ids={k:set() for k in keys}
    anchors=[]
    anchor_ids={k:set() for k in keys}
    writes={}
    for row in rows:
        if not _sequence(row) or len(row)<2 or not isinstance(row[1],str) or row[1] not in keys:
            raise ValueError('Malformed row or unknown context')
        kind,key,*f=row
        if kind=='META':
            if key in meta or len(f)!=16 or f[14:]!=['true','false']:
                raise ValueError('Missing, duplicate or inactive context metadata')
            values=[_integer(x) for x in f[:14]]
            if any(values[i]!=0 for i in ERROR_FIELDS):
                raise ValueError('Diagnostic/runtime coverage error')
            meta[key]=values
        elif kind=='SAMPLE':
            if len(f)!=6 or not isinstance(f[1],str) or f[5]!='false':
                raise ValueError('Malformed or failed sample')
            index=_integer(f[0]);a,z,d=(_number(x,exported=True) for x in f[2:5])
            if index<1 or index in sample_ids[key] or z<a:
                raise ValueError('Duplicate sample identity or reversed interval')
            sample_ids[key].add(index);samples.append((key,a,z,d))
        elif kind=='ANCHOR':
            if len(f)!=4:raise ValueError('Malformed activation anchor')
            index,p,t=(_integer(x) for x in f[:3]);at=_number(f[3],exported=True)
            if index<1 or index in anchor_ids[key]:raise ValueError('Duplicate anchor identity')
            anchor_ids[key].add(index);anchors.append((key,p,t,at))
        elif kind=='WRITE':
            if len(f)!=3 or not isinstance(f[1],str) or not f[1]:raise ValueError('Malformed write bucket')
            turn,count=_integer(f[0]),_integer(f[2]);identity=(key,turn,f[1])
            if identity in writes or turn<turns[0]-1 or turn>closing_turn:
                raise ValueError('Duplicate or out-of-capture write bucket')
            writes[identity]=count
        else:
            raise ValueError('Unknown exported row kind')
    if set(meta)!=keys:raise ValueError('Missing context metadata')
    for key in keys:
        ids=sample_ids[key]
        if len(ids)!=meta[key][0] or ids!=set(range(1,len(ids)+1)):
            raise ValueError('Incomplete context sample sequence')
        aids=anchor_ids[key]
        if aids!=set(range(1,len(aids)+1)):raise ValueError('Incomplete anchor sequence')
        if sum(n for (k,_,_),n in writes.items() if k==key)!=meta[key][13]:
            raise ValueError('Native counter/bucket mismatch')
    if not _sequence(brackets):raise ValueError('Expected actual clock brackets')
    calibration={k:{'before':[],'after':[]} for k in keys}
    for b in brackets:
        if not isinstance(b,Mapping) or not isinstance(b.get('key'),str) or b['key'] not in keys or b.get('phase') not in ('before','after'):
            raise ValueError('Malformed clock bracket')
        calibration[b['key']][b['phase']].append(b.get('triple'))
    offsets={}
    bounds={}
    for key in keys:
        phases=calibration[key]
        if any(len(phases[p])<3 for p in ('before','after')):
            raise ValueError('Missing before/after clock evidence')
        result=intersect_offsets(phases['before']+phases['after'])
        if not result['consistent']:raise ValueError('Inconsistent constant clock offset')
        offsets[key]=result['lower_seconds']/2+result['upper_seconds']/2
        bounds[key]=result
    starts={}
    anchor_counts={}
    latest_closure=-math.inf
    for turn in [*turns,closing_turn]:
        times=[]
        anchor_counts[turn]={}
        for key in keys:
            local=[at-offsets[key] for k,p,t,at in anchors if k==key and p==pid and t==turn]
            if any(not math.isfinite(at) for at in local):raise ValueError('Mapped clock overflow')
            if not local:raise ValueError('Missing local activation or closing anchor')
            anchor_counts[turn][key]=len(local)
            first=min(local);times.append(first)
            if turn==closing_turn:latest_closure=max(latest_closure,first)
        starts[turn]=min(times)
    ordered=[*turns,closing_turn]
    if any(starts[b]<starts[a]+10 for a,b in zip(ordered,ordered[1:])):
        raise ValueError('Incomplete ten-second observation window')
    if cap_start>starts[turns[0]] or cap_stop<latest_closure:
        raise ValueError('Capture does not cover all complete turns')
    windows=[]
    for turn in turns:
        begin,end=starts[turn],starts[turn]+10
        intervals=[]
        for key,a,z,_ in samples:
            ui_a,ui_z=a-offsets[key],z-offsets[key]
            if not math.isfinite(ui_a) or not math.isfinite(ui_z):raise ValueError('Mapped sample clock overflow')
            lo=max(begin,ui_a);hi=min(end,ui_z)
            if hi>=lo:intervals.append((lo,hi))
        windows.append({'turn':turn,'start_ui':begin,'end_ui':end,'observed_union_ms':union_seconds(intervals)*1000,
                        'clipped_inclusive_sum_ms_not_cpu':sum(z-a for a,z in intervals)*1000,
                        'sample_rows_intersecting':len(intervals)})
    def write_turn(turn):
        selected=[(k,api,n) for (k,t,api),n in writes.items() if t==turn]
        return {'turn':turn,'calls':sum(n for _,_,n in selected),'by_context':{
            k:sum(n for key,_,n in selected if key==k) for k in sorted(keys) if any(key==k for key,_,_ in selected)}}
    complete=[write_turn(t) for t in turns]
    partial=[write_turn(t) for t in sorted({t for _,t,_ in writes if t not in turns})]
    return {'windows':windows,'complete_turn_writes':complete,'partial_turn_writes':partial,
            'clock_bounds':bounds,'local_anchor_counts':anchor_counts,'contexts':len(keys),'samples':len(samples),
            'observed_b_turn_budget_ok':all(w['observed_union_ms']<=1000 for w in windows),
            'observed_n_req_budget_ok':all(t['calls']<=64 for t in complete),
            'limits':['Observed numbers assume constant context offsets; midpoint alignment is not exact synchronization.',
                      'Clock granularity and timing uncertainty remain unknown.',
                      'Inclusive envelopes contain Native/vanilla callees; they are not exclusive mod CPU.',
                      'Source coverage and city-history classification require separate evidence.',
                      'Matched B_delta and full TC-036 acceptance are not established.']}
