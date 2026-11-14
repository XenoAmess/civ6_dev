"""Strictly qualify the independent source140 Stage A export."""
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path

TARGETS=('Admin.Run','Controller.RunNow')
ROOT_FIELDS={'source','enabled','retired','subscribed','bound','qualification_errors',
             'closing_actual_turn','capture_start','capture_stop','anchors','profile','samples'}
PROFILE_FIELDS={'capacity','aggregate_zero','total_calls','dropped','invalid_clock','zero_success'}
SAMPLE_FIELDS={'name','seconds','failed','started','ended','turnStart','turnEnd',
               'cityStart','cityEnd','anchor','windowEligible'}
V2_SAMPLE_FIELDS=SAMPLE_FIELDS|{'preAnchor','argumentCount','allowOrders'}


def _object(value,fields,label):
    if not isinstance(value,dict) or set(value)!=fields:
        raise ValueError(f'Unknown {label} fields')
    return value


def _integer(value,label):
    if type(value)is not int or not 0<=value<=2147483647:
        raise ValueError(f'Unknown {label} integer')
    return value


def _number(value,label):
    if type(value)not in (int,float):
        raise ValueError(f'Unknown {label} number')
    try:
        value=float(value)
    except OverflowError as exc:
        raise ValueError(f'Overflowing {label}') from exc
    if not math.isfinite(value):
        raise ValueError(f'Nonfinite {label}')
    return value


def analyze_plan_capture(data,*,expected_source_version=140):
    if type(expected_source_version)is not int or expected_source_version not in (140,141,142):raise ValueError('Expected source140,141 or142')
    if not isinstance(data,dict):
        raise ValueError('Unknown capture object')
    v2=data.get('source')==f'baiqi{expected_source_version}-stageA-v2'
    d=_object(data,ROOT_FIELDS|({'pre_anchor'}if v2 else set()),'capture')
    if d['source']not in (f'baiqi{expected_source_version}-stageA-v1',f'baiqi{expected_source_version}-stageA-v2'):
        raise ValueError('Unknown Stage A source')
    if (d['enabled']is not False or d['retired']is not False
            or d['subscribed']is not True or d['bound']is not True):
        raise ValueError('Unknown Stage A lifecycle')
    if _integer(d['qualification_errors'],'qualification errors')!=0:
        raise ValueError('Unqualified diagnostic reads')
    if _integer(d['closing_actual_turn'],'closing turn')!=91:
        raise ValueError('Missing closing actual91')
    pre=None
    if v2:
        pre=_object(d['pre_anchor'],{'pending','recorded','validated','errors'},'pre-anchor proof')
        for key,value in pre.items():_integer(value,'pre-anchor '+key)
        if pre['pending']!=0 or pre['errors']!=0 or pre['recorded']!=pre['validated']:
            raise ValueError('Unresolved or invalid pre-anchor proof')
    start=_number(d['capture_start'],'capture start');stop=_number(d['capture_stop'],'capture stop')
    anchors=_object(d['anchors'],{str(t)for t in range(86,92)},'anchors')
    a={t:_number(anchors[str(t)],'anchor')for t in range(86,92)}
    if (start>a[86] or stop<a[91] or start>stop
            or any(a[t]>=a[t+1]for t in range(86,91))):
        raise ValueError('Invalid native anchor/capture order')
    if any(a[t]+10<=a[t] or a[t]+10>a[t+1]for t in range(86,91)):
        raise ValueError('Incomplete fixed10s activity window')
    p=_object(d['profile'],PROFILE_FIELDS,'profile')
    if _integer(p['capacity'],'capacity')!=4096 or p['aggregate_zero']is not False:
        raise ValueError('Unexpected sample budget or aggregation')
    for key in ('dropped','invalid_clock','zero_success'):
        if _integer(p[key],key)!=0:
            raise ValueError(f'Incomplete profile: {key}')
    total=_integer(p['total_calls'],'total calls')
    rows=d['samples']
    if not isinstance(rows,list) or len(rows)!=total or total>4096:
        raise ValueError('Sample accounting/capacity mismatch')
    values={name:[]for name in TARGETS}
    coverage={name:{str(t):0 for t in range(86,91)}for name in TARGETS}
    classes={name:{'pure_ten':0,'10_to_11':0,'eleven_city':0,'turn_crossing':0,
                   'other_city_state':0,'outside_window':0}for name in TARGETS}
    if v2:
        for counts in classes.values():counts['before_native_anchor']=0
    pre_rows=0
    for index,row in enumerate(rows):
        s=_object(row,V2_SAMPLE_FIELDS if v2 else SAMPLE_FIELDS,'sample')
        name=s['name']
        if not isinstance(name,str) or name not in TARGETS:
            raise ValueError('Unknown planning target')
        if s['failed']is not False:
            raise ValueError('Failed planning call')
        if type(s['windowEligible'])is not bool:
            raise ValueError('Unknown window eligibility')
        left=_number(s['started'],'sample start');right=_number(s['ended'],'sample end')
        seconds=_number(s['seconds'],'duration')
        if (left<start or right>stop or right<left or seconds<0
                or abs((right-left)-seconds)>1e-6):
            raise ValueError('Invalid sample clock/duration')
        if not math.isfinite(seconds*1000):
            raise ValueError('Overflowing millisecond duration')
        before=_integer(s['turnStart'],'turn before');after=_integer(s['turnEnd'],'turn after')
        c0=_integer(s['cityStart'],'city before');c1=_integer(s['cityEnd'],'city after')
        if before not in range(86,91) or not before<=after<=91:
            raise ValueError('Invalid sample turn range')
        anchor=_number(s['anchor'],'sample anchor')
        if anchor!=a[before]:
            raise ValueError('Sample is not bound to its native anchor')
        if v2:
            if type(s['preAnchor'])is not bool:
                raise ValueError('Unknown pre-anchor row flag')
            argc=_integer(s['argumentCount'],'argument count')
            allowance=s['allowOrders']
            if type(allowance)is not str or allowance not in ('false','true','nil','other'):
                raise ValueError('Unknown original argument metadata')
            if s['preAnchor']:
                if (name!='Controller.RunNow' or argc!=1 or allowance!='false'
                        or s['windowEligible']is not False or left>=anchor or right>anchor
                        or before!=after):
                    raise ValueError('Invalid whole-call pre-anchor proof')
                classes[name]['before_native_anchor']+=1;pre_rows+=1
                continue
        if left<anchor:
            raise ValueError('Sample starts before its native anchor without proof')
        eligible=left<anchor+10
        if s['windowEligible']is not eligible:
            raise ValueError('Contradictory sample window flag')
        if not eligible:
            group='outside_window'
        else:
            coverage[name][str(before)]+=1
            if before!=after:group='turn_crossing'
            elif c0==10 and c1==10:
                group='pure_ten';values[name].append(seconds*1000)
            elif c0==10 and c1==11:group='10_to_11'
            elif c0==11 and c1==11:group='eleven_city'
            else:group='other_city_state'
        classes[name][group]+=1
    if v2 and pre_rows!=pre['validated']:
        raise ValueError('Pre-anchor proof accounting mismatch')
    result={}
    for name in TARGETS:
        ordered=sorted(values[name]);n=len(ordered)
        p95=ordered[math.ceil(.95*n)-1]if n else None
        p50=ordered[math.ceil(.5*n)-1]if n else None
        maximum=ordered[-1]if n else None
        above20=sum(1 for v in ordered if v>20)
        above50=sum(1 for v in ordered if v>50)
        result[name]={'pure_ten_count':n,'p50_ms':p50,'p95_ms':p95,'max_ms':maximum,
                      'above_20ms_count':above20,'above_50ms_count':above50,
                      'budget_ok':n>=100 and p95<=20 and maximum<=50}
    report={'source':d['source'],'sample_quality_ok':True,'samples':total,
            'classification_counts':classes,'eligible_calls_by_turn':coverage,
            'targets':result,'overall_budget_ok':all(v['budget_ok']for v in result.values()),
            'limits':'Independent planning-function inclusive wall-clock latency only; no B_turn, N_req, B_delta or whole TC-036 pass.'}
    if v2:report['pre_anchor']=dict(pre)
    return report


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--input',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True)
    p.add_argument('--expected-source-version',type=int,choices=(140,141,142),default=140)
    a=p.parse_args();result=analyze_plan_capture(json.loads(a.input.read_text(encoding='utf-8')),expected_source_version=a.expected_source_version)
    with a.output.open('x',encoding='utf-8')as f:json.dump(result,f,ensure_ascii=False,indent=2);f.write('\n')
    print(json.dumps(result,ensure_ascii=False))


if __name__=='__main__':
    main()
