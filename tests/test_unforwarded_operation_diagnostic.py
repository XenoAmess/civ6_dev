from pathlib import Path
import unittest
from lupa.lua51 import LuaRuntime as Lua51
from lupa.lua53 import LuaRuntime as Lua53
from test_civilian_read_unknown_diagnostics import world

ROOT=Path(__file__).resolve().parents[1]
SOURCE=(ROOT/'tools/lua/diagnostic_unforwarded_operation.lua').read_text(encoding='utf-8')


class UnforwardedOperationTests(unittest.TestCase):
    def each(self,code):
        for E in (Lua51,Lua53):
            with self.subTest(engine=E):
                lua=E();lua.globals().New=lua.execute(SOURCE);lua.execute(code)

    def test_no_target_forward_even_on_repeat_and_overflow(self):
        self.each("""
local writes=0;local U={RequestOperation=function()writes=writes+1;return 'live' end}
local I={Units={[60]={UnitType='UNIT_MISSIONARY'}}}
local u={GetOwner=function()return 0 end,GetID=function()return 3735581 end,GetUnitType=function()return 60 end}
local a=New(U,I,0,3735581,'UNIT_MISSIONARY',1592408602,2);assert(a.Arm(0,3735581,'UNIT_MISSIONARY',1592408602))
for i=1,65 do assert(select('#',U.RequestOperation(u,1592408602,nil,'p',nil))==0)end
local s=a.Read();assert(writes==0 and s.intercepted==65 and s.targetNativeForwarded==0 and s.dropped==63 and #s.rows==2 and s.enabled)
assert(s.rows[1].argumentCount==3 and s.rows[1].NativeForwarded==false)
s.rows[1].id=0;assert(a.Read().rows[1].id==3735581)
assert(not a.Arm(0,3735581,'UNIT_MISSIONARY',1592408602));assert(a.Retire())
""")

    def test_bounded_capture_preserves_arguments_and_failure_never_leaks_target_request(self):
        self.each("""
local writes,captures=0,0;local fail=false
local U={RequestOperation=function()writes=writes+1 end};local I={Units={[60]={UnitType='UNIT_MISSIONARY'}}}
local u={GetOwner=function()return 0 end,GetID=function()return 3735581 end,GetUnitType=function()return 60 end}
local capture=function(w,code,...)captures=captures+1;assert(w==u and code==1592408602 and select('#',...)==2);if fail then error('capture')end;return '77;0;3735581;4;1;true' end
local a=New(U,I,0,3735581,'UNIT_MISSIONARY',1592408602,2,capture);assert(a.Arm(0,3735581,'UNIT_MISSIONARY',1592408602))
U.RequestOperation(u,1592408602,nil,'x');assert(a.Read().rows[1].observation=='77;0;3735581;4;1;true')
fail=true;U.RequestOperation(u,1592408602,nil,'x');U.RequestOperation(u,1592408602,nil,'x')
assert(writes==0 and captures==2 and a.Read().intercepted==3 and a.Read().observationErrors==1 and a.Read().dropped==1)
assert(a.Retire())
""")

    def test_other_action_exact_args_nil_holes_returns_and_error_once(self):
        self.each("""
local function pack(...)return{n=select('#',...),...}end
local calls,args=0;local fail=false
local original=function(...)calls=calls+1;args=pack(...);if fail then error('native-once')end;return false,nil,7,nil end
local U={RequestOperation=original};local I={Units={[60]={UnitType='UNIT_MISSIONARY'}}}
local u={GetOwner=function()return 0 end,GetID=function()return 3735581 end,GetUnitType=function()return 60 end}
local a=New(U,I,0,3735581,'UNIT_MISSIONARY',1592408602,64);assert(a.Arm(0,3735581,'UNIT_MISSIONARY',1592408602))
local v=pack(U.RequestOperation(u,745019656,nil,'x',nil))
assert(v.n==4 and v[1]==false and v[2]==nil and v[3]==7 and v[4]==nil and calls==1)
assert(args.n==5 and args[1]==u and args[2]==745019656 and args[3]==nil and args[4]=='x'and args[5]==nil)
fail=true;local ok,e=pcall(U.RequestOperation,u,745019656);assert(not ok and tostring(e):find('native%-once')and calls==2 and a.Read().intercepted==0)
assert(a.Retire())
""")

    def test_other_identity_and_failed_identity_still_forward_without_false_zero_claim(self):
        self.each("""
local calls=0;local U={RequestOperation=function()calls=calls+1;return 'native' end};local I={Units={[60]={UnitType='UNIT_MISSIONARY'}}}
local u={GetOwner=function()return 1 end,GetID=function()return 3735581 end,GetUnitType=function()return 60 end}
local a=New(U,I,0,3735581,'UNIT_MISSIONARY',1592408602,64);assert(a.Arm(0,3735581,'UNIT_MISSIONARY',1592408602))
assert(U.RequestOperation(u,1592408602)=='native'and calls==1 and a.Read().intercepted==0)
u.GetOwner=function()error('identity')end;assert(U.RequestOperation(u,1592408602)=='native'and calls==2 and a.Read().identityErrors==1)
assert(a.Retire())
""")

    def test_owned_outer_observer_must_retire_first_foreign_binding_is_preserved(self):
        self.each("""
local original=function()return 'native' end;local U={RequestOperation=original};local I={Units={}}
local a=New(U,I,0,3735581,'UNIT_MISSIONARY',1592408602,64)
assert(not a.Arm(1,3735581,'UNIT_MISSIONARY',1592408602))
assert(a.Arm(0,3735581,'UNIT_MISSIONARY',1592408602))
local inner=U.RequestOperation;local outer=function(...)return inner(...)end;U.RequestOperation=outer
assert(not a.Retire()and U.RequestOperation==outer and not a.Read().retired)
U.RequestOperation=inner;assert(a.Retire()and U.RequestOperation==original and a.Retire())
""")

    def test_unarmed_is_transparent_and_retirement_does_not_rearm(self):
        self.each("""
local calls=0;local original=function()calls=calls+1;return 9 end;local U={RequestOperation=original}
local I={Units={[60]={UnitType='UNIT_MISSIONARY'}}}
local u={GetOwner=function()return 0 end,GetID=function()return 3735581 end,GetUnitType=function()return 60 end}
local a=New(U,I,0,3735581,'UNIT_MISSIONARY',1592408602,64)
assert(U.RequestOperation(u,1592408602)==9 and calls==1 and a.Read().targetNativeForwarded==1)
assert(a.Retire()and not a.Arm(0,3735581,'UNIT_MISSIONARY',1592408602))
assert(U.RequestOperation(u,1592408602)==9 and calls==2)
""")

    def test_real_controller_keeps_intercepted_request_armed_and_does_not_retry_after_restore(self):
        lua,w,c,logs=world(Lua53)
        a=lua.execute(SOURCE)(lua.globals().UnitManager,lua.globals().GameInfo,7,4,'UNIT_MISSIONARY',1592408602,64)
        self.assertTrue(a.Arm(7,4,'UNIT_MISSIONARY',1592408602)[0]);c.RunNow()
        self.assertEqual(a.Read().intercepted,1)
        self.assertEqual(a.Read().targetNativeForwarded,0)
        self.assertEqual(len(w.spreadRequests),0)
        lua.execute("assert(TestRelBridge.store['BAIQI_RELIGIOUS_INTENTS_V1'].operations['4'].stage=='ARMED')")
        for _ in range(10):c.Update(1.0)
        self.assertEqual(a.Read().intercepted,1)
        self.assertEqual((w.spreadCharges,w.missionaryMoves),(3,4))
        self.assertTrue(a.Retire()[0]);w.turn=2
        for _ in range(10):c.Update(1.0)
        self.assertEqual(len(w.spreadRequests),0,logs)
        lua.execute("assert(TestRelBridge.store['BAIQI_RELIGIOUS_INTENTS_V1'].operations['4'].stage=='ARMED')")
        self.assertFalse(any('|error|'in v for v in logs),logs)


if __name__=='__main__':unittest.main()
