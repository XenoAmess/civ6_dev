from pathlib import Path
import unittest
from lupa.lua53 import LuaRuntime

ROOT=Path(__file__).resolve().parents[1]


class EventFacadeTests(unittest.TestCase):
    def setUp(self):
        self.lua=LuaRuntime(unpack_returned_tuples=True)
        self.lua.globals().New=self.lua.execute((ROOT/'tools/lua/diagnostic_event_facade.lua').read_text(encoding='utf-8'))
        self.lua.execute('''
NativeError={sentinel=true};WrapCalls=0;HandlerCalls=0;Recorded=0;Enabled=true
function Pack(...) return {n=select('#',...),...} end
function MakeEvent()
 local e={handlers={},adds=0,removes=0,emits=0,tag='native',addArgs={},removeArgs={},emitArgs={}}
 e.Add=function(fn,...)
  e.adds=e.adds+1;e.addArgs=Pack(fn,...)
  if type(fn)~='function' or AddError then error(NativeError,0) end
  e.handlers[fn]=true;return false,nil,'add-tail',nil
 end
 e.Remove=function(fn,...)
  e.removes=e.removes+1;e.removeArgs=Pack(fn,...);e.handlers[fn]=nil
  if RemoveError then error(NativeError,0) end
  return false,nil,'remove-tail',nil
 end
 e.Fire=function(...) for fn in pairs(e.handlers) do fn(...) end end
 return setmetatable(e,{__call=function(self,...)
  assert(self==e);e.emits=e.emits+1;e.emitArgs=Pack(...)
  if EmitError then error(NativeError,0) end
  return false,nil,'emit-tail',nil
 end,__newindex=function() error(NativeError,0) end})
end
function Wrap(label,fn)
 WrapCalls=WrapCalls+1
 if WrapError then error(NativeError,0) end
 return function(...) if Enabled then Recorded=Recorded+1 end;return fn(...) end
end
Event=MakeEvent();Family={A=Event,scalar='keep',plain={flag=true}}
P,Stats=New(Family,Wrap,'Owned')
Fn=function(...) HandlerCalls=HandlerCalls+1;HandlerArgs=Pack(...) end
''')

    def test_lazy_factory_and_all_static_call_arguments_and_returns(self):
        self.lua.execute('''
assert(Event.adds==0 and Event.removes==0 and WrapCalls==0)
assert(P.scalar=='keep' and P.plain==Family.plain)
local e=P.A;assert(e==P.A and e~=Event and e.tag=='native')
local out=Pack(e.Add(Fn,'extra',nil));assert(out.n==4 and out[1]==false and out[3]=='add-tail' and out[4]==nil)
assert(Event.addArgs.n==3 and Event.addArgs[2]=='extra' and Event.addArgs[3]==nil)
local wrapped=Event.addArgs[1];assert(wrapped~=Fn)
local r=Pack(e.Remove(Fn,'remove-extra',nil));assert(r.n==4 and r[3]=='remove-tail' and Event.removeArgs.n==3 and Event.removeArgs[1]==wrapped)
assert(Family.A==Event and Stats.events==1 and Stats.callbacks==1)
''')

    def test_duplicate_adds_keep_identity_and_disabled_timing_keeps_subscription(self):
        self.lua.execute('''
P.A.Add(Fn);local first=Event.addArgs[1];P.A.Add(Fn);assert(Event.addArgs[1]==first and WrapCalls==1)
Event.Fire(1,nil,3,nil);assert(HandlerCalls==1 and HandlerArgs.n==4 and Recorded==1)
Enabled=false;Event.Fire(2);assert(HandlerCalls==2 and Recorded==1 and Event.adds==2)
P.A.Remove(Fn);assert(next(Event.handlers)==nil)
''')

    def test_captured_remove_and_changed_event_identity_stay_coherent(self):
        self.lua.execute('''
local old=Event;local remove=P.A.Remove;P.A.Add(Fn)
local other=MakeEvent();Family.A=other;P.A.Add(Fn)
assert(Stats.events==2 and next(old.handlers)~=nil and next(other.handlers)~=nil)
remove(Fn);assert(next(old.handlers)==nil and next(other.handlers)~=nil)
P.A.Remove(Fn);assert(next(other.handlers)==nil)
Family.A=old;assert(P.A.Remove==remove);P.A.Add(Fn);P.A.Remove(Fn);assert(next(old.handlers)==nil)
''')

    def test_event_capacity_preserves_old_versions_and_forwards_overflow(self):
        self.lua.execute('''
P,Stats=New(Family,Wrap,'Owned',{maxEvents=1,maxCallbacks=2})
local first=P.A;local old=Event;Family.A=MakeEvent();assert(P.A==Family.A and Stats.droppedEvents==1)
Family.A=old;assert(P.A==first and Stats.events==1)
Family.B=MakeEvent();assert(P.B==Family.B and Stats.events==1 and Stats.droppedEvents==2)
''')

    def test_callback_capacity_and_failed_wrapping_keep_native_identity(self):
        self.lua.execute('''
P,Stats=New(Family,Wrap,'Owned',{maxCallbacks=1})
WrapError=true;P.A.Add(Fn);assert(Event.addArgs[1]==Fn and Stats.wrapErrors==1)
WrapError=false;P.A.Add(Fn);assert(Event.addArgs[1]==Fn and WrapCalls==1)
local other=function() end;P.A.Add(other);P.A.Add(other)
assert(Event.addArgs[1]==other and Stats.callbacks==1 and Stats.droppedCallbacks==2)
P.A.Remove(other);P.A.Remove(Fn);assert(next(Event.handlers)==nil)
''')

    def test_native_event_and_family_calls_preserve_nil_returns_and_errors(self):
        self.lua.execute('''
local r=Pack(P.A(1,nil,3,nil));assert(r.n==4 and r[3]=='emit-tail' and Event.emitArgs.n==4 and Event.emits==1)
EmitError=true;local ok,err=pcall(function() P.A(9) end);assert(not ok and err==NativeError and Event.emits==2)
setmetatable(Family,{__call=function(self,...) assert(self==Family);return false,nil,'family-tail',nil end})
local f=Pack(P(1,nil));assert(f.n==4 and f[3]=='family-tail')
''')

    def test_invalid_callback_and_readonly_write_errors_pass_through(self):
        self.lua.execute('''
local ok,err=pcall(P.A.Add,7,nil);assert(not ok and err==NativeError and Event.addArgs.n==2 and WrapCalls==0)
local ok2,err2=pcall(function() P.A.unknown='x' end);assert(not ok2 and err2==NativeError)
P.extra='value';assert(Family.extra=='value')
AddError=true;local ok3,err3=pcall(P.A.Add,Fn);assert(not ok3 and err3==NativeError)
''')

    def test_nil_family_probe_failures_and_invalid_limits_do_not_emit(self):
        self.lua.execute('''
local p,s=New(nil,Wrap,'Absent');assert(p==nil and s.unavailable)
local weird=setmetatable({},{__index=function() error('not an event') end})
Family.weird=weird;assert(P.weird==weird and Stats.probeErrors==1)
for _,n in ipairs({-1,1.5,math.huge,4097}) do assert(not pcall(New,Family,Wrap,'X',{maxEvents=n})) end
assert(not pcall(New,false,Wrap,'X'))
assert(Event.adds==0 and Event.emits==0 and WrapCalls==0)
''')

    def test_actual_archaeology_receipt_consumer_captured_remove_and_reload(self):
        self.lua.execute('''
Family.GreatWorkCreated=Event;Events=P;include=function() return true end
local bridge={version=1,marker='baiqi-archaeology-intent-v1'}
ExposedMembers={BaiqiArchaeologyBridge=bridge}
BaiqiArchaeologyIntentGameplay={version=1,marker='baiqi-archaeology-core-v1',bridge=bridge,ObserveCreated=function(...) Observed=Pack(...) end}
''')
        source=(ROOT/'mod/Baiqi/Lua/BaiqiArchaeologyReceiptEvents.lua').read_text(encoding='utf-8')
        self.lua.globals().Module=self.lua.execute(source)
        self.lua.execute('Event.Fire(0,5898281,10,13,24,12);assert(Observed.n==6 and Observed[6]==12)')
        self.lua.globals().Module=self.lua.execute(source)
        self.lua.execute('''
local count=0;for _ in pairs(Event.handlers) do count=count+1 end;assert(count==1)
Module.Shutdown();assert(next(Event.handlers)==nil and Event.removes==2)
''')


if __name__=='__main__':
    unittest.main()
