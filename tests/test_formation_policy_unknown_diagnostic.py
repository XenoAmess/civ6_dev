from pathlib import Path
import unittest
from lupa.lua51 import LuaRuntime as Lua51
from lupa.lua53 import LuaRuntime as Lua53

ROOT=Path(__file__).resolve().parents[1]
HELPER=(ROOT/'tools/lua/diagnostic_formation_policy_unknown.lua').read_text(encoding='utf-8')
POLICY=(ROOT/'mod/Baiqi/Lua/BaiqiPolicy.lua').read_text(encoding='utf-8')

class FormationPolicyUnknownTests(unittest.TestCase):
    def vm(self,VM):
        v=VM();v.execute(POLICY);v.globals().New=v.execute(HELPER)
        v.execute("ctx={isBaiqi=true,activeTurn=true,enabled=true,player=0,localPlayer=0};unit={id=7274546,owner=0,type='UNIT_SETTLER',formationCount=1,moves=2,plot=716}")
        return v
    def test_actual_policy_positive_unknown_then_exact_restore(self):
        for VM in(Lua51,Lua53):
            for kind in('UNIT_SETTLER','UNIT_BUILDER','UNIT_MISSIONARY'):
                with self.subTest(VM=VM.__module__,kind=kind):
                    v=self.vm(VM);v.globals().kind=kind
                    v.execute("unit.type=kind;original=BaiqiPolicy.CanCivilian;assert(original(ctx,unit));api=New(BaiqiPolicy,0,7274546,kind,64);assert(api.Arm(0,7274546,kind));local ok,why=BaiqiPolicy.CanCivilian(ctx,unit);assert(ok==false and why=='formation_or_unknown'and unit.formationCount==1);local s=api.Snapshot();assert(s.masked==1 and s.rows[1].formation==1 and s.rows[1].allowed==false and s.rows[1].reason=='formation_or_unknown'and s.rows[1].returnCount==2);assert(api.Retire());assert(BaiqiPolicy.CanCivilian==original and original(ctx,unit));assert(not api.Arm(0,7274546,kind))")
    def test_nonpositive_inactive_formed_foreign_and_nonplain_do_not_consume(self):
        for VM in(Lua51,Lua53):
            for change in('unit.moves=0','unit.moves=-1','unit.moves=0/0','unit.moves=math.huge','unit.formationCount=2','unit.owner=1','unit.id=999',"unit.type='UNIT_SCOUT'",'ctx.activeTurn=false','setmetatable(unit,{})'):
                with self.subTest(VM=VM.__module__,change=change):
                    v=self.vm(VM);v.execute("api=New(BaiqiPolicy,0,7274546,'UNIT_SETTLER',64);assert(api.Arm(0,7274546,'UNIT_SETTLER'))");v.execute(change);v.execute("for i=1,100 do BaiqiPolicy.CanCivilian(ctx,unit)end;local s=api.Snapshot();assert(s.masked==0 and s.enabled and not s.expired and #s.rows==0)")
    def test_bound_expiry_and_rows_copy_do_not_rearm(self):
        for VM in(Lua51,Lua53):
            with self.subTest(VM=VM.__module__):
                v=self.vm(VM);v.execute("api=New(BaiqiPolicy,0,7274546,'UNIT_SETTLER',2);assert(api.Arm(0,7274546,'UNIT_SETTLER'));assert(not BaiqiPolicy.CanCivilian(ctx,unit));assert(not BaiqiPolicy.CanCivilian(ctx,unit));local s=api.Snapshot();assert(s.masked==2 and s.expired and not s.enabled and #s.rows==2);s.rows[1].moves=999;assert(api.Snapshot().rows[1].moves==2);assert(BaiqiPolicy.CanCivilian(ctx,unit));assert(not api.Arm(0,7274546,'UNIT_SETTLER'));assert(api.Retire())")
    def test_varargs_returns_errors_and_original_called_once(self):
        for VM in(Lua51,Lua53):
            with self.subTest(VM=VM.__module__):
                v=self.vm(VM);v.execute("calls=0;BaiqiPolicy.CanCivilian=function(c,u,...)calls=calls+1;assert(c==ctx and u~=unit and u.formationCount==nil and unit.formationCount==1);assert(select('#',...)==3);local a,b,z=...;assert(a==nil and b==false and z=='tail');return nil,false,'end',nil end;local original=BaiqiPolicy.CanCivilian;api=New(BaiqiPolicy,0,7274546,'UNIT_SETTLER',64);assert(api.Arm(0,7274546,'UNIT_SETTLER'));local function pack(...)return{n=select('#',...),...}end;local r=pack(BaiqiPolicy.CanCivilian(ctx,unit,nil,false,'tail'));assert(calls==1 and r.n==4 and r[1]==nil and r[2]==false and r[3]=='end'and r[4]==nil);assert(api.Retire()and BaiqiPolicy.CanCivilian==original)")
                v=self.vm(VM);v.execute("calls=0;BaiqiPolicy.CanCivilian=function()calls=calls+1;error('original-policy-failure')end;api=New(BaiqiPolicy,0,7274546,'UNIT_SETTLER',64);assert(api.Arm(0,7274546,'UNIT_SETTLER'));local ok,e=pcall(BaiqiPolicy.CanCivilian,ctx,unit);assert(not ok and tostring(e):find('original%-policy%-failure')and calls==1);assert(api.Retire())")
    def test_foreign_binding_not_overwritten(self):
        for VM in(Lua51,Lua53):
            with self.subTest(VM=VM.__module__):
                v=self.vm(VM);v.execute("api=New(BaiqiPolicy,0,7274546,'UNIT_SETTLER',64);local foreign=function()return'foreign'end;BaiqiPolicy.CanCivilian=foreign;local ok,why=api.Retire();assert(ok==false and why=='foreign_binding_preserved'and BaiqiPolicy.CanCivilian==foreign);assert(not api.Arm(0,7274546,'UNIT_SETTLER'))")
    def test_context_binding_change_does_not_mask(self):
        for VM in(Lua51,Lua53):
            with self.subTest(VM=VM.__module__):
                v=self.vm(VM);v.execute("api=New(BaiqiPolicy,0,7274546,'UNIT_SETTLER',64);assert(api.Arm(0,7274546,'UNIT_SETTLER'));BaiqiPolicy.Context=function()return true end;BaiqiPolicy.CanCivilian(ctx,unit);local s=api.Snapshot();assert(not s.contextBinding and s.masked==0);assert(api.Retire())")

if __name__=='__main__':unittest.main()
