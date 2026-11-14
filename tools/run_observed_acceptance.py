"""Continuous private diagnostic experiment using an injected, owned Tuner client.

All end-turn actions belong to TEST_PLAYER. This tool never commands units,
chooses diplomacy, or changes the mod's mandatory domestic delegation.

Ordinary mode requires request_normal_end(turn, token). The callback handles the
test-player queue outside this observer and returns exactly {turn, token,
requested: True, forced: False} after reading the ordinary END call-return
receipt. This records issuance; engine acceptance and activation remain
separate observations. The independent poll must still observe activation.
Unknown outcomes abort without replay. Historical UserForced reproduction
requires explicit legacy_forced=True and cannot be combined with the callback.
"""
from datetime import datetime,timezone
import hashlib
import json
from pathlib import Path
import uuid


def _payload(messages,marker):
    found=[]
    for message in messages:
        if message['tag']==3 and message['payload'].startswith('ERR:'):
            raise RuntimeError(message['payload'])
        if message['tag']==-1:
            line=message['payload'].split(': ',1)[-1]
            if line.startswith(marker+'\t'):
                found.append(line.split('\t')[1:])
    if len(found)!=1:
        raise RuntimeError(f'Expected one {marker} receipt, got {len(found)}')
    return found[0]


def run(query,is_diplomacy_visible,now,sleep,emit,ledger_dir: Path,*,sample_budget=None,
        request_normal_end=None,legacy_forced=False,pressure_initial_turn=None):
    if type(legacy_forced) is not bool:
        raise TypeError('legacy_forced must be an explicit boolean')
    if legacy_forced:
        if request_normal_end is not None:
            raise ValueError('Choose one TEST_PLAYER end-turn mode')
    elif not callable(request_normal_end):
        raise TypeError('An ordinary TEST_PLAYER end-turn callback is required')
    if sample_budget is not None and (type(sample_budget) is not int or sample_budget<1):
        raise ValueError('Expected positive retained-sample budget')
    pressure=pressure_initial_turn is not None
    if pressure and(type(pressure_initial_turn)is not int or not 0<=pressure_initial_turn<=2147483641
                    or legacy_forced or sample_budget!=4096):
        raise ValueError('Pressure requires bounded actual calendar, ordinary END and4096 cap')
    first=pressure_initial_turn if pressure else 85;closing=first+6
    token=uuid.uuid4().hex
    quoted=json.dumps(token)
    requested=[]
    attempted=False
    build_guard=f'''local pressureBuild=P6Q20PressureBuild
assert(type(pressureBuild)=='table' and pressureBuild.source=='baiqi142-pressure-observed-v1'
 and pressureBuild.source_version==142 and pressureBuild.initial_turn=={first})
'''if pressure else''
    stage_guard=(build_guard+f'''assert(s.source=='baiqi142-pressure-observed-v1' and s.source_version==142 and s.initial_turn=={first})
''')if pressure else''
    ledger_dir=Path(ledger_dir)
    ledger_dir.mkdir(parents=True,exist_ok=True)

    def diplomacy():
        visible=is_diplomacy_visible()
        if type(visible) is not bool:
            raise RuntimeError('Diplomacy visibility unavailable')
        return visible

    def action(turn,code):
        nonlocal attempted
        record={'at_utc':datetime.now(timezone.utc).isoformat(),'role':'TEST_PLAYER',
                'turn':turn,'token':token,'status':'ABOUT_TO_SUBMIT_ONCE',
                'mode':'LEGACY_USER_FORCED' if legacy_forced else 'ORDINARY_CALLBACK',
                'lua_sha256':hashlib.sha256(code.encode('utf-8')).hexdigest()}
        if pressure:record.update(source='baiqi142-pressure-observed-v1',source_version=142,initial_turn=first)
        with (ledger_dir/f'end{turn}.json').open('x',encoding='utf-8',newline='\n') as stream:
            json.dump(record,stream,indent=2);stream.write('\n')
        attempted=True
        marker='P6_Q20_END' if legacy_forced else 'P6_Q20_READY'
        result=_payload(query('BaiqiExecutor',code),marker)
        if result!=[str(turn)]:
            raise RuntimeError('Unexpected end-turn receipt')
        if not legacy_forced:
            # The callback owns ordinary queue handling and reads its native END
            # call-return receipt. Unknown outcomes stop capture; no retry.
            ack=request_normal_end(turn,token)
            if (type(ack) is not dict or set(ack)!={'turn','token','requested','forced'}
                or type(ack['turn']) is not int or ack['turn']!=turn or ack['token']!=token
                or ack['requested'] is not True or ack['forced'] is not False):
                raise RuntimeError('Ordinary END acknowledgement unavailable')
        requested.append(turn)
        emit(f'TEST_PLAYER_END_REQUESTED_ONCE {turn} mode={record["mode"]}')

    def end_code(turn):
        submit=("assert(type(UI.RequestAction)=='function' and ActionTypes.ACTION_ENDTURN~=nil)\n"
                "UI.RequestAction(ActionTypes.ACTION_ENDTURN,{REASON='UserForced'})\n"
                f"print('P6_Q20_END',{turn})" if legacy_forced else f"print('P6_Q20_READY',{turn})")
        return f'''
local s=P6Q20StageB;assert(s and s.token=={quoted} and s.phase=='RECORDING')
{stage_guard}
assert(Game.GetLocalPlayer()==0 and Game.GetCurrentGameTurn()=={turn})
assert(not UI.IsGameCoreBusy() and not UI.IsProcessingMessages() and not s.ends[{turn}])
s.ends[{turn}]=true
{submit}
'''

    budget_start=''
    budget_each=''
    budget_finish=''
    if sample_budget is not None:
        budget_start='local sampleQuotaTotal=0\n'
        budget_each='''assert(clean.profile.aggregateZero==true and clean.profile.zeroSuccess==0 and type(clean.profile.capacity)=='number' and clean.profile.capacity>=1 and clean.profile.capacity==math.floor(clean.profile.capacity))
 sampleQuotaTotal=sampleQuotaTotal+clean.profile.capacity
'''
        budget_finish=f'assert(sampleQuotaTotal<={sample_budget})\n'
    setup=f'''
assert(Game.GetLocalPlayer()==0 and Game.GetCurrentGameTurn()=={first} and Players[0]:GetCities():GetCount()==10)
assert(not UI.IsGameCoreBusy() and not UI.IsProcessingMessages() and P6Q20StageB==nil)
{build_guard}
local registry=ExposedMembers.P6BaiqiOwnRegistry
assert(registry.marker=='baiqi67-q19' and registry.enabled==false)
local keys={{}};for key in pairs(registry.entries) do keys[#keys+1]=key end;table.sort(keys)
assert(#keys==32 or (#keys==33 and registry.entries['UI/BaiqiWorldCrisisPopup.lua']~=nil))
local s={{keys=keys,token={quoted},phase='PREPARING',ends={{}},baseline={{}},start=Automation.GetTime()}}
P6Q20StageB=s
{budget_start}
for _,key in ipairs(keys) do
 local e=registry.entries[key];local v=e.Snapshot()
 assert(v.marker=='baiqi67-q19' and v.enabled==false and v.retired==false and v.subscribed and v.stats.registryErrors==0 and v.stats.anchorErrors==0)
 e.Reset()
 local clean=e.Snapshot()
 assert(clean.profile.totalCalls==0 and clean.profile.dropped==0 and clean.profile.invalidClock==0 and #clean.profile.samples==0 and #clean.anchors==0)
 assert(clean.stats.registryErrors==0 and clean.stats.anchorErrors==0 and clean.stats.anchorDropped==0 and clean.stats.bucketErrors==0 and clean.stats.bucketDropped==0)
 assert(clean.leaves.dropped==0 and clean.leaves.wrapErrors==0 and clean.leaves.enabledErrors==0)
 for _,counter in ipairs(clean.leaves.counters) do assert(counter.totalCalls==0 and counter.callbackErrors==0) end
 {budget_each}
 for i=1,3 do local a=Automation.GetTime();local c=e.ReadClock();local z=Automation.GetTime()
  print('P6_Q20_CLOCK_BEFORE',key,i,string.format('%.17g',a),string.format('%.17g',c),string.format('%.17g',z))
 end
end
{budget_finish}
for _,u in Players[0]:GetUnits():Members() do
 local row=GameInfo.Units[u:GetUnitType()]
 if row and not BaiqiPolicy.CivilianType(row.UnitType) then
  s.baseline[#s.baseline+1]={{id=u:GetID(),kind=row.UnitType,x=u:GetX(),y=u:GetY(),moves=u:GetMovesRemaining()}}
  print('P6_Q20_ARMY_BEFORE',u:GetID(),row.UnitType,u:GetX(),u:GetY(),u:GetMovesRemaining())
 end
end
registry.enabled=true
for _,key in ipairs(keys) do assert(registry.entries[key].SetEnabled(true)) end
s.phase='RECORDING'
'''
    if pressure:
        setup=setup.replace('P6Q20StageB=s',f"s.source='baiqi142-pressure-observed-v1';s.source_version=142;s.initial_turn={first};\nP6Q20StageB=s",1)
        setup=setup.replace('local s={',"assert(#keys==33 and registry.entries['UI/BaiqiWorldCrisisPopup.lua']~=nil)\nlocal s={",1)
    poll=f'''
local s=P6Q20StageB;assert(s and s.token=={quoted} and s.phase=='RECORDING')
{stage_guard}
local registry=ExposedMembers.P6BaiqiOwnRegistry
local errors,total=0,0
local function Integer(v) return type(v)=='number' and v>=0 and v<math.huge and v==math.floor(v) end
for _,key in ipairs(s.keys) do
 local e=registry.entries[key]
 local ok,v=pcall(e and e.Snapshot)
 if not ok or type(v)~='table' or type(v.profile)~='table' or type(v.stats)~='table' or type(v.leaves)~='table' then errors=errors+1
 else
  if v.enabled~=true or v.retired~=false or v.subscribed~=true then errors=errors+1 end
  if Integer(v.profile.totalCalls) then total=total+v.profile.totalCalls else errors=errors+1 end
  for _,pair in ipairs({{{{v.profile,'dropped'}},{{v.profile,'invalidClock'}},{{v.stats,'registryErrors'}},{{v.stats,'anchorErrors'}},
   {{v.stats,'anchorDropped'}},{{v.stats,'bucketErrors'}},{{v.stats,'bucketDropped'}},{{v.leaves,'dropped'}},{{v.leaves,'wrapErrors'}},{{v.leaves,'enabledErrors'}}}}) do
   local value=pair[1][pair[2]];if Integer(value) then errors=errors+value else errors=errors+1 end
  end
  if type(v.leaves.counters)~='table' then errors=errors+1
  else for _,counter in ipairs(v.leaves.counters) do
   local value=counter.callbackErrors;if Integer(value) then errors=errors+value else errors=errors+1 end
  end end
 end
end
if registry.enabled~=true then errors=errors+1 end
local turn=Game.GetCurrentGameTurn()
local ui=registry.entries['UI/BaiqiExecutor.lua'].Snapshot()
local anchor
for _,a in ipairs(ui.anchors) do if a.pid==0 and a.turn==turn then anchor=a.time;break end end
local age=anchor and Automation.GetTime()-anchor or -1
print('P6_Q20_STATE',turn,string.format('%.17g',age),anchor~=nil,errors,total,Players[0]:GetCities():GetCount(),not UI.IsGameCoreBusy() and not UI.IsProcessingMessages())
'''
    def stop_code(phase,calibrate):
        code=f'''
local s=P6Q20StageB
if not s or s.token~={quoted} then print('P6_Q20_STOP','SKIPPED_FOREIGN');return end
{stage_guard if calibrate else ''}
local registry=ExposedMembers.P6BaiqiOwnRegistry
assert(registry.marker=='baiqi67-q19')
registry.enabled=false
for _,key in ipairs(s.keys) do assert(registry.entries[key].SetEnabled(false)) end
s.phase={json.dumps(phase)};s.stop=Automation.GetTime()
'''
        if calibrate:
            code+='''
for _,key in ipairs(s.keys) do local e=registry.entries[key]
 for i=1,3 do local a=Automation.GetTime();local c=e.ReadClock();local z=Automation.GetTime()
  print('P6_Q20_CLOCK_AFTER',key,i,string.format('%.17g',a),string.format('%.17g',c),string.format('%.17g',z))
 end
end
'''
        return code+"print('P6_Q20_STOP',s.phase,Game.GetCurrentGameTurn())\n"

    try:
        if diplomacy():
            raise RuntimeError('Close current diplomacy as TEST_PLAYER before starting')
        action(first,setup+end_code(first))
        deadline=now()+180
        last_turn=first
        waiting_diplomacy=False
        while now()<deadline:
            try:
                fields=_payload(query('BaiqiExecutor',poll),'P6_Q20_STATE')
            except (OSError,EOFError) as error:
                emit(f'READONLY_POLL_TRANSPORT {type(error).__name__}')
                sleep(1);continue
            if len(fields)!=7:
                raise RuntimeError('Malformed state receipt')
            turn,age=int(fields[0]),float(fields[1])
            anchored=fields[2]=='true'
            errors,samples,cities=int(fields[3]),int(fields[4]),int(fields[5])
            ready=fields[6]=='true'
            emit(f'Q20_STATE turn={turn} age={age:.3f} samples={samples} cities={cities} errors={errors}')
            if errors:
                raise RuntimeError('Diagnostic coverage error; budget remains unknown')
            if turn<last_turn or turn>closing:
                raise RuntimeError('Unexpected game turn')
            if turn!=last_turn:
                last_turn=turn;deadline=now()+180
            if turn==closing and anchored:
                stopped=_payload(query('BaiqiExecutor',stop_code('COMPLETE',True)),'P6_Q20_STOP')
                if stopped!=['COMPLETE',str(closing)]:
                    raise RuntimeError('Completion stop not confirmed')
                result={'phase':'COMPLETE','turn':closing,'requested_turns':requested,'samples':samples,'cities':cities,'token':token}
                if pressure:result.update(source='baiqi142-pressure-observed-v1',source_version=142,initial_turn=first,
                                          window_turns=list(range(first+1,first+6)),closing_turn=closing)
                return result
            # A visit can arrive after END was issued and hold its transition.
            # Keep reporting visibility while awaiting actual activation; this
            # never grants another callback or repeats the earlier END.
            visible=diplomacy()
            if visible:
                if not waiting_diplomacy:emit(f'TEST_PLAYER_DIPLOMACY_ACTIVE turn={turn}')
                waiting_diplomacy=True
            else:
                waiting_diplomacy=False
                if first+1<=turn<=first+5 and anchored and age>=10 and ready and turn not in requested:
                    action(turn,end_code(turn));deadline=now()+180
            sleep(1)
        raise TimeoutError('Activation or TEST_PLAYER diplomacy wait exceeded 180 seconds')
    except BaseException:
        if attempted:
            try:
                result=_payload(query('BaiqiExecutor',stop_code('ABORTED',False)),'P6_Q20_STOP')
                emit('ABORT_RECORDING_STOP '+json.dumps(result))
            except BaseException as error:
                emit('ABORT_RECORDING_STOP_UNCONFIRMED '+type(error).__name__)
        raise
