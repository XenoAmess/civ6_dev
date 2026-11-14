"""TEST_PLAYER-only paired run; injected client is the sole Native writer."""
from __future__ import annotations
from pathlib import Path
import json,uuid,math
from tools.run_observed_acceptance import _payload


def run(query,is_diplomacy_visible,close_diplomacy,now,sleep,emit,ledger_dir: Path,*,variant,fixture_sha256,
        request_normal_end=None,legacy_forced=False,expected_source_version=140):
    if type(expected_source_version)is not int or expected_source_version not in (140,141):raise ValueError('Invalid source version')
    if type(legacy_forced)is not bool:raise TypeError('legacy_forced must be an explicit boolean')
    if legacy_forced:
        if request_normal_end is not None:raise ValueError('Legacy forced mode cannot use normal callback')
    elif not callable(request_normal_end):raise TypeError('Ordinary paired run requires request_normal_end callback')
    if variant not in ('enabled','control'):raise ValueError('Invalid paired variant')
    if not isinstance(fixture_sha256,str) or len(fixture_sha256)!=64 or any(c not in '0123456789abcdef' for c in fixture_sha256):raise ValueError('Expected fixture hash')
    token=uuid.uuid4().hex;quoted=json.dumps(token);requested=[];attempted=False;actual_source_version=None
    ledger_dir.mkdir(parents=True,exist_ok=False)

    def action(turn,prefix=''):
        nonlocal attempted,actual_source_version
        with (ledger_dir/f'end-{turn}.json').open('x',encoding='utf-8',newline='\n') as f:
            json.dump({'role':'TEST_PLAYER','turn':turn,'token':token,'status':'ATTEMPTED_BEFORE_NATIVE',
                       'mode':'LEGACY_USER_FORCED'if legacy_forced else'ORDINARY_CALLBACK'},f);f.write('\n')
        attempted=True
        common=prefix+f'''
local s=P6PairStage;assert(s and s.token=={quoted} and s.phase=='RECORDING' and not s.ends[{turn}])
assert(Game.GetLocalPlayer()==0 and Game.GetCurrentGameTurn()=={turn})
assert(not UI.IsGameCoreBusy() and not UI.IsProcessingMessages())
'''
        if legacy_forced:
            code=common+f'''
assert(P6PairClock:Begin({turn}))
s.ends[{turn}]=true
UI.RequestAction(ActionTypes.ACTION_ENDTURN,{{REASON='UserForced'}})
print('P6_PAIR_END',{turn})
'''
            receipt=_payload(query('BaiqiExecutor',code),'P6_PAIR_END')
            if receipt!=[str(turn)]:raise RuntimeError('Unknown end-turn action ACK; do not replay')
        else:
            code=common+f'''
assert(Players[0]:IsTurnActive() and s.source_version=={expected_source_version} and s.normal_end==true and P6PairSourceVersion=={expected_source_version})
local owner=P6PairEndOwner;assert(owner and owner.active and owner.errors==0 and owner.refused==0
 and owner.entry==ExposedMembers.P6BaiqiPairEndBridge and owner.entry.source_version=={expected_source_version})
local c=P6PairClock:Snapshot();assert(c.pending==nil and #c.records=={turn-85} and c.errors==0 and c.refused==0 and c.subscribed and not c.retired)
s.ends[{turn}]=true
print('P6_PAIR_READY',{turn},P6PairSourceVersion)
'''
            receipt=_payload(query('BaiqiExecutor',code),'P6_PAIR_READY')
            if receipt!=[str(turn),str(expected_source_version)]:raise RuntimeError('Unknown ordinary READY reservation; no callback or retry')
            actual_source_version=expected_source_version
            ack=request_normal_end(turn,token)
            if (type(ack)is not dict or set(ack)!={'turn','token','requested','forced'}
                    or type(ack['turn'])is not int or ack['turn']!=turn or ack['token']!=token
                    or ack['requested']is not True or ack['forced']is not False):
                raise RuntimeError('Unknown ordinary issuance receipt; do not replay')
            post=f'''
local s=P6PairStage;assert(s and s.token=={quoted} and s.phase=='RECORDING')
local owner=P6PairEndOwner;assert(owner.active and owner.errors==0 and owner.refused==0
 and owner.entry==ExposedMembers.P6BaiqiPairEndBridge)
local c=P6PairClock:Snapshot();local p=c.pending;local last=c.records[#c.records]
assert(c.errors==0 and c.refused==0 and c.subscribed and not c.retired)
assert((p and p.from_turn=={turn} and p.to_turn=={turn+1} and p.pid==0)
 or(last and last.from_turn=={turn} and last.to_turn=={turn+1} and last.pid==0))
print('P6_PAIR_ISSUANCE_CLOCK',{turn})
'''
            if _payload(query('BaiqiExecutor',post),'P6_PAIR_ISSUANCE_CLOCK')!=[str(turn)]:
                raise RuntimeError('Ordinary clock start unknown; do not replay')
        requested.append(turn);emit(f'TEST_PLAYER_PAIR_END_ONCE {turn}')

    setup=f'''
assert(Game.GetLocalPlayer()==0 and Game.GetCurrentGameTurn()==85 and Players[0]:GetCities():GetCount()==10)
assert(P6PairStage==nil or P6PairStage.phase=='COMPLETE')
local c=P6PairClock:Snapshot()
assert(c.marker=='baiqi67-paired-clock-v1' and c.subscribed and not c.retired and c.errors==0 and c.refused==0 and #c.records==0 and c.pending==nil)
local s={{token={quoted},phase='RECORDING',ends={{}},baseline={{}},start=Automation.GetTime()}}
s.normal_end={str(not legacy_forced).lower()};s.source_version=P6PairSourceVersion
'''+('''assert(P6PairSourceVersion==VERSION and P6PairEndOwner and P6PairEndOwner.active
 and P6PairEndOwner.errors==0 and P6PairEndOwner.refused==0)
'''.replace('VERSION',str(expected_source_version))if not legacy_forced else'')+'''
P6PairStage=s
for _,u in Players[0]:GetUnits():Members() do local row=GameInfo.Units[u:GetUnitType()]
 if row and not BaiqiPolicy.CivilianType(row.UnitType) then s.baseline[#s.baseline+1]={id=u:GetID(),x=u:GetX(),y=u:GetY()} end end
'''
    poll=f'''
local s=P6PairStage;assert(s and s.token=={quoted} and s.phase=='RECORDING')
local c=P6PairClock:Snapshot();local turn=Game.GetCurrentGameTurn();local last=c.records[#c.records]
local age=(last and last.to_turn==turn) and Automation.GetTime()-last.ended or -1
print('P6_PAIR_STATE',turn,#c.records,string.format('%.17g',age),c.errors,c.refused,c.subscribed,c.retired,c.pending~=nil,not UI.IsGameCoreBusy() and not UI.IsProcessingMessages(),Players[0]:GetCities():GetCount())
'''
    ordinary_retire=''
    if not legacy_forced:
        ordinary_retire="assert(P6PairEndOwner.active and P6PairEndOwner.errors==0 and P6PairEndOwner.refused==0);assert(P6PairEndOwner.Retire() and not P6PairEndOwner.active);"
    stop=f'''
local s=P6PairStage;assert(s and s.token=={quoted} and s.phase=='RECORDING')
local c=P6PairClock:Snapshot();assert(Game.GetCurrentGameTurn()==90 and #c.records==5 and c.pending==nil and c.errors==0 and c.refused==0)
for turn=85,89 do assert(s.ends[turn]==true) end;assert(not s.ends[90])
for _,record in ipairs(c.records) do print('P6_PAIR_RECORD',record.from_turn,record.to_turn,record.pid,string.format('%.17g',record.started),string.format('%.17g',record.ended),string.format('%.17g',record.seconds)) end
{ordinary_retire}
assert(P6PairClock:Retire());local final=P6PairClock:Snapshot()
assert(final.errors==0 and final.retired and not final.subscribed)
s.phase='COMPLETE';s.stop=Automation.GetTime()
print('P6_PAIR_META',final.errors,final.refused,final.retired,final.subscribed,Game.GetCurrentGameTurn(),Players[0]:GetCities():GetCount())
'''
    closing_visit=False
    try:
        if is_diplomacy_visible() is not False:raise RuntimeError('Current diplomacy requires TEST_PLAYER before setup')
        action(85,setup);deadline=now()+180;last_turn=85
        while now()<deadline:
            visible=is_diplomacy_visible()
            if type(visible) is not bool:raise RuntimeError('Diplomacy visibility unknown')
            if visible and not closing_visit:
                # One external QA-player close per observed visit, never product AI.
                with (ledger_dir/f'diplomacy-{len(list(ledger_dir.glob("diplomacy-*.json")))}.json').open('x',encoding='utf-8',newline='\n') as f:
                    json.dump({'role':'TEST_PLAYER','token':token,'status':'ATTEMPTED_BEFORE_NATIVE'},f);f.write('\n')
                closing_visit=True;close_diplomacy();emit('TEST_PLAYER_PAIR_DIPLOMACY_CLOSE_REQUESTED'if legacy_forced else'TEST_PLAYER_PAIR_DIPLOMACY_CALLBACK_RETURNED')
            if not visible and closing_visit:closing_visit=False;emit('TEST_PLAYER_PAIR_DIPLOMACY_HIDDEN_CONFIRMED')
            try:fields=_payload(query('BaiqiExecutor',poll),'P6_PAIR_STATE')
            except (OSError,EOFError) as error:emit('PAIR_READONLY_POLL '+type(error).__name__);sleep(.25);continue
            if len(fields)!=10:raise RuntimeError('Malformed paired state')
            turn,count=int(fields[0]),int(fields[1]);age=float(fields[2])
            if not math.isfinite(age) or int(fields[3])!=0 or int(fields[4])!=0 or fields[5:7]!=['true','false'] or fields[7] not in ('true','false') or fields[8] not in ('true','false'):raise RuntimeError('Paired clock metadata invalid')
            if turn<last_turn or turn>90 or count<0 or count>5:raise RuntimeError('Unexpected paired turn/sample count')
            if turn!=last_turn:last_turn=turn;deadline=now()+180
            emit(f'PAIR_STATE turn={turn} records={count} age={age:.3f} cities={fields[9]} diplomacy={visible}')
            if fields[7]=='false' and count==turn-85 and age>=10 and fields[8]=='true' and not visible:
                if turn==90:
                    messages=query('BaiqiExecutor',stop);meta=_payload(messages,'P6_PAIR_META')
                    if meta[:5]!=['0','0','true','false','90'] or len(meta)!=6:raise RuntimeError('Paired stop not confirmed')
                    records=[]
                    for message in messages:
                        if message['tag']!=-1:continue
                        parts=message['payload'].split(': ',1)[-1].split('\t')
                        if parts[0]=='P6_PAIR_RECORD':
                            if len(parts)!=7:raise RuntimeError('Malformed paired record')
                            records.append(dict(zip(('from_turn','to_turn','pid','started','ended','seconds'),[int(v) for v in parts[1:4]]+[float(v) for v in parts[4:]])))
                    if len(records)!=5:raise RuntimeError('Incomplete paired capture')
                    return {'variant':variant,'run_id':variant+'-'+token,'fixture_sha256':fixture_sha256,'source_version':actual_source_version,'errors':0,'refused':0,'records':records,'requested_turns':requested,'cities':int(meta[5]),'phase':'COMPLETE','token':token,
                            'end_mode':'LEGACY_USER_FORCED'if legacy_forced else'ORDINARY_CALLBACK','forced':legacy_forced}
                if turn not in requested:action(turn);deadline=now()+180
            sleep(.25)
        raise TimeoutError('Paired activation or TEST_PLAYER UI wait exceeded180seconds')
    except BaseException:
        if attempted:
            bridge_cleanup=''if legacy_forced else"print('P6_PAIR_BRIDGE_ABORT',P6PairEndOwner and P6PairEndOwner.Retire()or false);"
            cleanup=f'''local s=P6PairStage
if s and s.token=={quoted} then s.phase='ABORTED';{bridge_cleanup}print('P6_PAIR_ABORT',P6PairClock:Retire())
else print('P6_PAIR_ABORT','SKIPPED_FOREIGN') end'''
            try:
                messages=query('BaiqiExecutor',cleanup)
                result=_payload(messages,'P6_PAIR_ABORT')
                if result not in (['true'],['false'],['SKIPPED_FOREIGN']):raise RuntimeError('Bad abort receipt')
                if not legacy_forced and result!=['SKIPPED_FOREIGN']:
                    bridge=_payload(messages,'P6_PAIR_BRIDGE_ABORT')
                    if bridge not in (['true'],['false']):raise RuntimeError('Bad bridge abort receipt')
                    emit('PAIR_ABORT_BRIDGE_RETIRE_RECEIPT '+json.dumps(bridge))
                emit('PAIR_ABORT_RETIRE_RECEIPT '+json.dumps(result))
            except BaseException as error:emit('PAIR_ABORT_RETIRE_UNCONFIRMED '+type(error).__name__)
        raise
