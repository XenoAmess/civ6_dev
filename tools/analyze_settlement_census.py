"""Qualify one observed settlement search, without granting global legality."""
from __future__ import annotations
import math

CALLERS=('recruit_choice','recruit_write','settler_alternatives')
FLAGS=('first_only','one_validation','preferred_supplied','excluded_supplied',
       'ai_available','exhausted','failed')
COUNTS=('raw_hints','admitted','visited','cheap_pass','support_true',
        'support_false','support_unknown','returned')
METADATA=('turn_start','turn_end','cities_start','cities_end')
KINDS=('NOT_CALLED','nil','table','boolean','number','string','userdata','function','thread')
FIELDS={'caller','hints_kind','started','ended',*FLAGS,*COUNTS,*METADATA}


def classify_settlement_call(row):
    if not isinstance(row,dict) or set(row)!=FIELDS:
        raise ValueError('Unknown or missing census row fields')
    for key in FLAGS:
        if type(row[key])is not bool:raise ValueError('Unknown census flag: '+key)
    for key in COUNTS+METADATA:
        if type(row[key])is not int or not 0<=row[key]<=2147483647:
            raise ValueError('Unknown census integer: '+key)
    clock=[]
    for key in ('started','ended'):
        if type(row[key])not in (int,float):raise ValueError('Unknown census clock')
        try:value=float(row[key]);known=math.isfinite(value)
        except OverflowError:known=False
        if not known:raise ValueError('Nonfinite census clock')
        clock.append(value)
    if (clock[1]<clock[0] or not math.isfinite(clock[1]-clock[0])
        or row['turn_end']<row['turn_start']):raise ValueError('Invalid census interval')
    if type(row['caller'])is not str or row['caller']not in CALLERS:
        raise ValueError('Unknown census caller')
    if type(row['hints_kind'])is not str or row['hints_kind']not in KINDS:
        raise ValueError('Unknown census hints type')
    if row['failed']:raise ValueError('Failed call cannot qualify pressure')
    if (row['hints_kind']=='NOT_CALLED')==row['ai_available']:
        raise ValueError('Contradictory AI/query state')
    if not row['ai_available'] and any(row[k]for k in COUNTS):
        raise ValueError('Counters without AI')
    if row['hints_kind']!='table' and row['raw_hints']!=0:
        raise ValueError('Rows without recommendation table')
    if not 0<=row['cheap_pass']<=row['visited']<=row['admitted']<=row['raw_hints']+int(row['preferred_supplied']):
        raise ValueError('Contradictory census denominators')
    if sum(row[k]for k in ('support_true','support_false','support_unknown'))!=row['cheap_pass']:
        raise ValueError('Incomplete support accounting')
    if row['returned']!=row['support_true'] or(row['first_only']and row['returned']>1):
        raise ValueError('Contradictory returned proposals')
    if row['one_validation']and(not row['first_only']or not row['excluded_supplied']or row['cheap_pass']>1):
        raise ValueError('Contradictory sliced search')
    if row['exhausted']!=(row['visited']==row['admitted']):
        raise ValueError('Contradictory exhaustion')
    if row['returned']>0:outcome='HAS_ACCEPTED_SITE'
    elif not row['ai_available']or row['hints_kind']!='table'or row['support_unknown']>0:outcome='UNKNOWN'
    elif not row['exhausted']:outcome='PARTIAL_UNVISITED'
    elif row['admitted']==0:outcome='EMPTY_OBSERVED_POOL'
    else:outcome='EXHAUSTED_NO_ACCEPTED_SITE_IN_POOL'
    return {'caller':row['caller'],'outcome':outcome,'many_candidate_pool':row['admitted']>=12,
            'global_no_legal_site':None,'visited':row['visited'],'unvisited':row['admitted']-row['visited']}
