"""SDK contract doubles for the actual private experiment driver; no live client."""
from pathlib import Path
import xml.etree.ElementTree as ET
from lupa.lua53 import LuaRuntime

ROOT=Path(__file__).resolve().parents[1]


class DriverHarness:
    def __init__(self):
        self.lua=LuaRuntime(unpack_returned_tuples=True)
        self.actions=[]
        self.action_times=[]
        self.anchor_times={}
        self.recordings=[]
        self.logs=[]
        self.queries=[]
        self.visibility_queries=0
        self.visibility=lambda h:False
        self.fail_poll_once=False
        self.raise_after_action_turn=None
        self.advance=True
        self.activation_delay=0
        self.drop_at_turn=None
        self.pending=[]
        self.messages=[]
        self.lua.globals().OnAction=self._on_action
        self.lua.globals().CapturePrint=self._print
        self.lua.globals().CaptureRecording=lambda key,value:self.recordings.append((key,value,int(self.world.turn)))
        self.lua.execute('''unpack=table.unpack;table.unpack=nil
World={turn=85,clock=120.125,dropCount=0,diplomacy=false,anchors={}}
Game={GetLocalPlayer=function() return 0 end,GetCurrentGameTurn=function() return World.turn end}
Automation={GetTime=function() return World.clock end}
Players={[0]={GetCities=function() return {GetCount=function() return 10 end} end,
 GetUnits=function() return {Members=function() return function() return nil end end} end}}
GameInfo={Units={}};BaiqiPolicy={CivilianType=function() return false end}
UI={IsGameCoreBusy=function() return false end,IsProcessingMessages=function() return false end,
 RequestAction=function(a,p) OnAction(a,p) end}
ActionTypes={ACTION_ENDTURN=1}
ExposedMembers={P6BaiqiOwnRegistry={marker='baiqi67-q19',entries={},enabled=false}}
print=function(...) CapturePrint(...) end
function AddFakeContext(key)
 local enabled=false
 local p={samples={},totalCalls=0,dropped=0,invalidClock=0,capacity=128,aggregateZero=true,zeroSuccess=0}
 local stats={registryErrors=0,anchorErrors=0,anchorDropped=0,bucketErrors=0,bucketDropped=0}
 local leaves={entries=0,dropped=0,wrapErrors=0,enabledErrors=0,counters={}}
 local entry={marker='baiqi67-q19'}
 entry.Snapshot=function()
  p.dropped=World.dropCount
  return {key=key,marker='baiqi67-q19',enabled=enabled,retired=false,subscribed=true,
   profile=p,stats=stats,leaves=leaves,anchors=World.anchors,buckets={}}
 end
 entry.SetEnabled=function(value) assert(type(value)=='boolean');enabled=value;CaptureRecording(key,value);return true end
 entry.Reset=function() assert(not enabled);World.anchors={} end
 entry.ReadClock=function() return World.clock end
 ExposedMembers.P6BaiqiOwnRegistry.entries[key]=entry
end''')
        self.world=self.lua.globals().World
        info=ET.fromstring((ROOT/'mod/Baiqi/Baiqi.modinfo').read_bytes())
        self.keys=[e.findtext('Properties/LuaReplace') for e in info.findall('InGameActions/ReplaceUIScript')]
        self.keys+=['UI/BaiqiExecutor.lua','Lua/BaiqiGameplay.lua']
        assert len(self.keys)==33 and 'UI/BaiqiWorldCrisisPopup.lua' in self.keys
        from tools.diagnostic_quotas import bounded_quotas
        quotas=bounded_quotas(self.keys)
        for key in self.keys:
            self.lua.globals().AddFakeContext(key)
            self.lua.globals().ExposedMembers.P6BaiqiOwnRegistry.entries[key].Snapshot().profile.capacity=quotas[key]

    def _print(self,*values):
        def text(v):
            if v is True:return 'true'
            if v is False:return 'false'
            if v is None:return 'nil'
            return str(v)
        self.messages.append({'tag':-1,'payload':'O\0BaiqiExecutor: '+'\t'.join(text(v) for v in values)})

    def _anchor(self,turn):
        a=self.world.anchors
        a[len(a)+1]=self.lua.table_from({'pid':0,'turn':turn,'time':self.world.clock})
        self.anchor_times[turn]=float(self.world.clock)

    def _on_action(self,action,params):
        assert action==1 and params.REASON=='UserForced'
        assert not self.world.diplomacy,'End turn attempted behind visible diplomacy'
        self.actions.append(int(self.world.turn))
        self.action_times.append((int(self.world.turn),float(self.world.clock)))
        if self.advance:
            self.world.turn+=1
            if self.drop_at_turn==self.world.turn:self.world.dropCount=1
            if self.activation_delay:
                self.pending.append((int(self.world.turn),float(self.world.clock)+self.activation_delay))
            else:self._anchor(int(self.world.turn))

    def query(self,context,code):
        assert context=='BaiqiExecutor' and isinstance(code,str)
        self.queries.append(code)
        if self.fail_poll_once and 'P6_Q20_STATE' in code:
            self.fail_poll_once=False
            raise OSError('simulated readonly socket failure')
        before=len(self.actions)
        self.messages=[]
        self.lua.execute(code)
        if len(self.actions)>before and self.actions[-1]==self.raise_after_action_turn:
            raise OSError('simulated lost action acknowledgement after execution')
        return self.messages+[{'tag':3,'payload':''}]

    def diplomacy_visible(self):
        self.visibility_queries+=1
        value=self.visibility(self)
        if type(value) is bool:self.world.diplomacy=value
        return value

    def now(self):return float(self.world.clock)

    def sleep(self,seconds):
        assert 0<=seconds<=1
        self.world.clock+=seconds
        for turn,at in list(self.pending):
            if self.world.clock>=at:
                self._anchor(turn);self.pending.remove((turn,at))

    def emit(self,message):self.logs.append(message)

    def all_recording(self,value):
        entries=self.lua.globals().ExposedMembers.P6BaiqiOwnRegistry.entries
        return all(entries[key].Snapshot().enabled is value for key in self.keys)
