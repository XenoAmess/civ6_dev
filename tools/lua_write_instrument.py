"""Observe known source67 Native write references in a private diagnostic copy."""
from bisect import bisect_right
import re
from tools.lua_function_instrument import tokens,lua_string

STATIC={
    'UnitManager':{'RequestOperation','RequestCommand','FinishMoves'},
    'CityManager':{'RequestOperation','RequestCommand','TransferCity'},
    'UI':{'RequestPlayerOperation'},
    'Game':{'SetProperty'},
    'NativeUnit':{'RequestOperation','RequestCommand'},
    'NativeCity':{'RequestOperation','RequestCommand'},
    'NativeUI':{'RequestPlayerOperation'},
}
OBJECT={'SetProperty','ChangeGoldBalance','AttachModifierByID',
        'RequestChangeGovernment','SetGovernmentChangeConsidered','RequestPolicyChanges'}
ALIASES={'NativeUnit':'UnitManager','NativeCity':'CityManager','NativeUI':'UI'}


def instrument_writes(source: str,label: str) -> tuple[str,list[dict]]:
    if not isinstance(source,str) or not isinstance(label,str):
        raise ValueError('Source and label must be strings')
    ts=tokens(source)
    if any(t.value in ('P6WriteRef','P6WriteMethod') for t in ts):
        raise ValueError('Diagnostic helper collision')
    newlines=[i for i,c in enumerate(source) if c=='\n']
    edits=[]
    manifest=[]
    for i,t in enumerate(ts):
        if t.value in STATIC and i+2<len(ts) and ts[i+1].value=='.' and ts[i+2].value in STATIC[t.value]:
            method=ts[i+2].value
            before=ts[i-1].value if i else None
            after=ts[i+3].value if i+3<len(ts) else None
            if before in ('.',':','function') or after=='=':
                raise ValueError('Unsupported qualified SDK receiver or assignment')
            line=bisect_right(newlines,t.start)+1
            canonical=ALIASES.get(t.value,t.value)
            title=f'{label}:{line}:{canonical}.{method}'
            skip=t.value in ('UnitManager','CityManager','UI') and method not in ('FinishMoves','TransferCity')
            edits.append((t.start,ts[i+2].end,f'P6WriteRef({lua_string(title)},{source[t.start:ts[i+2].end]},{str(skip).lower()})'))
            manifest.append({'label':title,'line':line,'kind':'static_ref','receiver':t.value,'method':method,'skip_guard':skip})
        if t.value in OBJECT and i>0 and ts[i-1].value==':':
            if i<2 or i+1>=len(ts) or ts[i+1].value!='(':
                raise ValueError('Unsupported object method syntax')
            receiver=ts[i-2]
            before=ts[i-3].value if i>=3 else None
            if not re.fullmatch(r'[A-Za-z_][A-Za-z_0-9]*',receiver.value) or before in ('.',':','function'):
                raise ValueError('Unsupported complex object receiver or declaration')
            line=bisect_right(newlines,receiver.start)+1
            title=f'{label}:{line}:{t.value}'
            edits.append((receiver.start,t.end,f'P6WriteMethod({lua_string(title)},{receiver.value},{lua_string(t.value)})'))
            manifest.append({'label':title,'line':line,'kind':'object_call','receiver':receiver.value,'method':t.value,'skip_guard':False})
    for start,end,replacement in sorted(edits,reverse=True):
        source=source[:start]+replacement+source[end:]
    return source,manifest
