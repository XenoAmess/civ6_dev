from pathlib import Path
import uuid
from lupa.lua53 import LuaRuntime
from tools.build_static_control import clock_prelude

ROOT=Path(__file__).resolve().parents[1]


class Harness:
    def __init__(self,*,visit=False,lose_end=None,close_unknown=False,never_activate=False):
        self.lua=LuaRuntime(unpack_returned_tuples=True);self.lose_end=lose_end;self.close_unknown=close_unknown;self.never_activate=never_activate
        self.close_calls=0;self.messages=[];self.ledger=ROOT/'.local-model/paired-driver-tests'/uuid.uuid4().hex
        self.lua.execute('''
T={time=1000,turn=85,actions={},logs={},callbacks={},diplomacy=false,clockCalls=0}
Events={PlayerTurnActivated={Add=function(fn) T.callbacks[#T.callbacks+1]=fn end,Remove=function(fn) for i=#T.callbacks,1,-1 do if T.callbacks[i]==fn then table.remove(T.callbacks,i) end end end}}
Game={GetCurrentGameTurn=function() return T.turn end,GetLocalPlayer=function() return 0 end}
Automation={GetTime=function() T.clockCalls=T.clockCalls+1;if T.clockError or T.clockCalls==T.clockFailAt then error('clock') end;return T.time end}
GameInfo={Units={}};BaiqiPolicy={CivilianType=function() return false end}
Players={[0]={GetCities=function() return {GetCount=function() return 10 end} end,GetUnits=function() return {Members=function() return function() end end} end}}
ActionTypes={ACTION_ENDTURN=2}
UI={IsGameCoreBusy=function() return false end,IsProcessingMessages=function() return false end,
 RequestAction=function(action,args) assert(action==2 and args.REASON=='UserForced');T.actions[#T.actions+1]=T.turn;T.nextAt=T.time+2;if T.visit and T.turn==87 then T.diplomacy=true end end}
print=function(...) local a={...};for i=1,select('#',...) do a[i]=tostring(a[i]) end;T.logs[#T.logs+1]=table.concat(a,'\t') end
''')
        self.lua.execute(clock_prelude());self.t=self.lua.globals().T;self.t.visit=visit

    def query(self,context,code):
        assert context=='BaiqiExecutor';self.t.logs=self.lua.table()
        self.lua.execute(code)
        if self.lose_end is not None and 'UI.RequestAction' in code and self.t.actions[len(self.t.actions)]==self.lose_end:
            self.lose_end=None;raise OSError('Native action executed but ACK unknown')
        return [{'tag':-1,'payload':'O\0BaiqiExecutor: '+line} for line in self.t.logs.values()]+[{'tag':3,'payload':''}]

    def now(self):return self.t.time
    def sleep(self,seconds):
        self.t.time+=seconds
        if self.t.closeAt is not None and self.t.time>=self.t.closeAt:self.t.diplomacy=False;self.t.closeAt=None
        if not self.never_activate and not self.t.diplomacy and self.t.nextAt is not None and self.t.time>=self.t.nextAt:
            self.t.turn+=1;self.t.nextAt=None
            self.lua.execute('for _,fn in ipairs(T.callbacks) do fn(1);fn(0,false) end')
    def visible(self):return bool(self.t.diplomacy)
    def close(self):
        self.close_calls+=1;self.t.closeAt=self.t.time+.75
        if self.close_unknown:raise OSError('Diplomacy close ACK unknown')
    def emit(self,message):self.messages.append(message)
