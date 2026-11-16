"""Private faults preserve real consumers and Native ABI, and never write game state."""
from pathlib import Path
import unittest

from lupa.lua51 import LuaRuntime as Lua51
from lupa.lua53 import LuaRuntime as Lua53
from religious_intent_harness import install_religious_bridge

ROOT=Path(__file__).resolve().parents[1]
OWNER=(ROOT/'tools/lua/diagnostic_owner_unknown.lua').read_text(encoding='utf-8')
LEGAL=(ROOT/'tools/lua/diagnostic_legality_unknown.lua').read_text(encoding='utf-8')


def world(runtime,controller_source=None):
    lua=runtime(unpack_returned_tuples=True);logs=[]
    lua.globals().print=lambda *args:logs.append(' '.join(map(str,args)))
    for name in ('mock_world','mock_missionary'):
        lua.execute((ROOT/f'tests/lua/{name}.lua').read_text(encoding='utf-8'))
    install_religious_bridge(lua)
    for name in ('BaiqiConfig','BaiqiPolicy','BaiqiPlanner','BaiqiController'):
        code=controller_source if name=='BaiqiController'and controller_source is not None else (ROOT/f'mod/Baiqi/Lua/{name}.lua').read_text(encoding='utf-8')
        lua.execute(code)
    w=lua.globals().TestWorld;w.withMissionary=True
    return lua,w,lua.globals().BaiqiController,logs


class ReadUnknownConsumerTests(unittest.TestCase):
    def test_owner_copy_reaches_real_controller_denial_and_exact_restore_recovers(self):
        # The existing isolated religious Core harness loads environments with
        # Lua 5.3's load signature. Helper transparency below covers both VMs.
        for runtime in (Lua53,):
            with self.subTest(runtime=runtime):
                lua,w,c,logs=world(runtime)
                api=lua.execute(OWNER)(lua.globals().BaiqiPolicy,7,4,'UNIT_MISSIONARY',64)
                self.assertEqual(api.Arm(7,4,'UNIT_MISSIONARY'),(True,'armed'))
                for _ in range(4):c.RunNow()
                self.assertGreater(api.Snapshot().masked,0)
                self.assertEqual((len(w.unitRequests),len(w.spreadRequests)),(0,0),logs)
                self.assertEqual(w.objects.missionary.GetOwner(),7)
                self.assertEqual(api.Retire(),(True,'restored'));c.RunNow()
                self.assertEqual(len(w.spreadRequests),1,logs)
                self.assertFalse(any('|error|'in v for v in logs),logs)

    def test_unknown_spread_is_denied_by_real_controller_without_preparing_spread(self):
        for runtime in (Lua53,):
            with self.subTest(runtime=runtime):
                lua,w,c,logs=world(runtime)
                api=lua.execute(LEGAL)(lua.globals().UnitManager,lua.globals().GameInfo,7,4,'UNIT_MISSIONARY',1592408602,64)
                self.assertTrue(api.Arm(7,4,'UNIT_MISSIONARY')[0]);c.RunNow()
                self.assertGreater(api.Snapshot().masked,0)
                self.assertEqual(len(w.spreadRequests),0,logs)
                # A separately qualified standby may still run; it is not a spread.
                self.assertTrue(all(v.op!=1592408602 for v in w.unitRequests.values()))
                self.assertTrue(api.Retire()[0])
                self.assertTrue(lua.globals().UnitManager.CanStartOperation(w.objects.missionary,1592408602,None))
                self.assertFalse(any('|error|'in v for v in logs),logs)


class ReadUnknownTransparencyTests(unittest.TestCase):
    def run_lua(self,source,test):
        for runtime in (Lua51,Lua53):
            with self.subTest(runtime=runtime):
                lua=runtime();lua.globals().New=lua.execute(source);lua.execute(test)

    def test_policy_copy_preserves_input_context_varargs_returns_bounds_and_foreign_binding(self):
        self.run_lua(OWNER,r'''
local function pack(...)return{n=select('#',...),...}end
local seen,calls={},0;local ctx={player=7};local originalSnapshot={owner=7,id=4,type='UNIT_MISSIONARY',formationCount=1,moves=4,plot=42}
local original=function(c,s,...)calls=calls+1;assert(c==ctx);seen=pack(s,...);return s.owner==7,nil,'tail',nil end
local P={CanCivilian=original};local a=New(P,7,4,'UNIT_MISSIONARY',2)
assert(P.CanCivilian(ctx,originalSnapshot)==true and calls==1 and a.Snapshot().masked==0)
assert(not a.Arm(8,4,'UNIT_MISSIONARY'));assert(a.Arm(7,4,'UNIT_MISSIONARY'))
local v=pack(P.CanCivilian(ctx,originalSnapshot,nil,'x',nil));assert(v.n==4 and v[1]==false and v[2]==nil and v[3]=='tail'and v[4]==nil)
assert(seen.n==4 and seen[1]~=originalSnapshot and seen[1].owner==nil and seen[1].moves==4 and seen[2]==nil and seen[3]=='x'and seen[4]==nil)
assert(originalSnapshot.owner==7 and calls==2)
assert(P.CanCivilian(ctx,originalSnapshot)==false);local s=a.Snapshot();assert(s.masked==2 and s.expired and not s.enabled)
s.rows[1].owner=0;assert(a.Snapshot().rows[1].owner==7)
assert(P.CanCivilian(ctx,originalSnapshot)==true and calls==4);assert(not a.Arm(7,4,'UNIT_MISSIONARY'))
local owned=P.CanCivilian;local foreign=function()end;P.CanCivilian=foreign
assert(not a.Retire()and P.CanCivilian==foreign and not a.Snapshot().retired)
P.CanCivilian=owned;assert(a.Retire()and P.CanCivilian==original);assert(a.Retire())
''')

    def test_policy_original_error_propagates_once_and_other_identity_is_untouched(self):
        self.run_lua(OWNER,r'''
local calls=0;local target={owner=7,id=4,type='UNIT_MISSIONARY'}
local P={CanCivilian=function(c,s)calls=calls+1;assert(s==target);error('policy-original')end}
local a=New(P,7,99,'UNIT_MISSIONARY',64);assert(a.Arm(7,99,'UNIT_MISSIONARY'))
local ok,e=pcall(P.CanCivilian,{},target);assert(not ok and tostring(e):find('policy%-original')and calls==1 and a.Snapshot().masked==0)
assert(a.Retire())
''')

    def test_native_exact_call_returns_nil_holes_positive_only_mask_and_read_original(self):
        self.run_lua(LEGAL,r'''
local function pack(...)return{n=select('#',...),...}end
local calls=0;local args;local allowed=true
local original=function(...)calls=calls+1;args=pack(...);return allowed,nil,'tail',nil end
local U={CanStartOperation=original};local I={Units={[60]={UnitType='UNIT_MISSIONARY'}}}
local u={GetOwner=function()return 7 end,GetID=function()return 4 end,GetUnitType=function()return 60 end}
local a=New(U,I,7,4,'UNIT_MISSIONARY',1592408602,2)
local v=pack(U.CanStartOperation(u,1592408602,nil,{},nil));assert(v.n==4 and v[1]==true and calls==1 and args.n==5)
assert(a.Arm(7,4,'UNIT_MISSIONARY'));v=pack(U.CanStartOperation(u,1592408602,nil,{},nil))
assert(v.n==4 and v[1]==nil and v[2]==nil and v[3]=='tail'and v[4]==nil and calls==2 and args.n==5 and args[3]==nil and args[5]==nil)
v=pack(a.ReadOriginal(u,1592408602,nil));assert(v[1]==true and calls==3 and args.n==3 and a.Snapshot().masked==1 and a.Snapshot().probes==1)
allowed=false;assert(U.CanStartOperation(u,1592408602,nil)==false and a.Snapshot().masked==1)
allowed=true;assert(U.CanStartOperation(u,8,nil)==true and a.Snapshot().masked==1)
assert(U.CanStartOperation(u,1592408602,nil)==nil);local s=a.Snapshot();assert(s.expired and s.masked==2 and #s.rows==2)
s.rows[1].id=9;assert(a.Snapshot().rows[1].id==4)
assert(U.CanStartOperation(u,1592408602,nil)==true);assert(a.Retire()and U.CanStartOperation==original and a.Retire())
''')

    def test_native_error_no_retry_and_identity_failure_still_forwards(self):
        self.run_lua(LEGAL,r'''
local calls=0;local fail=true
local original=function()calls=calls+1;if fail then error('native-original')end;return true end
local U={CanStartOperation=original};local I={Units={}};local u={GetUnitType=function()error('getter')end}
local a=New(U,I,7,4,'UNIT_MISSIONARY',1592408602,64);assert(a.Arm(7,4,'UNIT_MISSIONARY'))
local ok,e=pcall(U.CanStartOperation,u,1592408602,nil);assert(not ok and tostring(e):find('native%-original')and calls==1 and a.Snapshot().masked==0)
fail=false;assert(U.CanStartOperation(u,1592408602,nil)==true and calls==2 and a.Snapshot().identityErrors==1)
assert(a.Retire())
''')

    def test_native_foreign_binding_and_wrong_actor_cannot_be_overwritten_or_probed(self):
        self.run_lua(LEGAL,r'''
local original=function()return true end;local U={CanStartOperation=original};local I={Units={[60]={UnitType='UNIT_MISSIONARY'}}}
local u={GetOwner=function()return 8 end,GetID=function()return 4 end,GetUnitType=function()return 60 end}
local a=New(U,I,7,4,'UNIT_MISSIONARY',1592408602,64);assert(a.Arm(7,4,'UNIT_MISSIONARY'))
assert(U.CanStartOperation(u,1592408602,nil)==true and a.Snapshot().masked==0)
assert(not pcall(a.ReadOriginal,u,1592408602,nil))
local owned=U.CanStartOperation;local foreign=function()end;U.CanStartOperation=foreign
assert(not a.Retire()and U.CanStartOperation==foreign and not a.Snapshot().retired)
assert(not pcall(a.ReadOriginal,u,1592408602,nil));U.CanStartOperation=owned;assert(a.Retire())
''')


if __name__=='__main__':unittest.main()
