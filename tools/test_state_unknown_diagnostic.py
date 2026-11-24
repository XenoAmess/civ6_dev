"""Software faults for the private F07 adapter; no running-game interaction."""
from pathlib import Path
import unittest
from lupa.lua51 import LuaRuntime as Lua51
from lupa.lua53 import LuaRuntime as Lua53
from tools.build_state_unknown_mod import transform,restore_release,ORIGINAL_READ,PRIVATE_READ
from tools.build_formation_unknown_mod import SNAPSHOT_SOURCE,ANCHOR

ROOT=Path(__file__).resolve().parents[1]
SETUP=r'''
local n={snapshot=0,qualify=0}
local s={owner=0,id=3735581,type='UNIT_MISSIONARY',formationCount=1,moves=4,plot=646}
local unit={value=s}
local function snapshot(u,ctx)n.snapshot=n.snapshot+1;return u.value end
local function qualifier(u,op,...)n.qualify=n.qualify+1;n.args={n=select('#',...),...};return true,nil,'native',nil end
local api=Factory(snapshot,qualifier,0,3735581,'UNIT_MISSIONARY',1592408602,64)
local function pack(...)return{n=select('#',...),...}end
'''

class StateUnknownTests(unittest.TestCase):
    def run_lua(self,body):
        for name,VM in [('Lua51',Lua51),('Lua53',Lua53)]:
            with self.subTest(VM=name):
                vm=VM();vm.globals().Factory=vm.execute((ROOT/'tools/lua/diagnostic_state_unknown.lua').read_text(encoding='utf-8'));vm.execute(SETUP+body)

    def test_only_copies_exact_ready_snapshot_and_never_changes_original(self):
        self.run_lua(r'''
assert(api.Snapshot(unit,{})==s and n.snapshot==1)
assert(api.Arm(0,3735581,'UNIT_MISSIONARY','owner'))
local changed=api.Snapshot(unit,{})
assert(changed~=s and changed.owner==nil and s.owner==0 and changed.id==s.id and changed.moves==4)
unit.value={owner=1,id=3735581,type='UNIT_MISSIONARY',formationCount=1,moves=4};assert(api.Snapshot(unit,{})==unit.value)
unit.value={owner=0,id=3735582,type='UNIT_MISSIONARY',formationCount=1,moves=4};assert(api.Snapshot(unit,{})==unit.value)
unit.value={owner=0,id=3735581,type='UNIT_APOSTLE',formationCount=1,moves=4};assert(api.Snapshot(unit,{})==unit.value)
unit.value={owner=0,id=3735581,type='UNIT_MISSIONARY',formationCount=2,moves=4};assert(api.Snapshot(unit,{})==unit.value)
unit.value={owner=0,id=3735581,type='UNIT_MISSIONARY',formationCount=1,moves=0};assert(api.Snapshot(unit,{})==unit.value)
assert(api.Read().masked.owner==1 and n.qualify==0)
''')

    def test_modes_are_explicit_single_use_and_state_exports_are_detached(self):
        self.run_lua(r'''
assert(not api.Arm(1,3735581,'UNIT_MISSIONARY','owner'))
assert(not api.Arm(0,3735581,'UNIT_MISSIONARY','unknown'))
assert(api.Arm(0,3735581,'UNIT_MISSIONARY','formation'))
assert(api.Snapshot(unit,{}).formationCount==nil and s.formationCount==1)
assert(not api.Arm(0,3735581,'UNIT_MISSIONARY','formation'))
local v=api.Read();v.masked.formation=999;v.rows[1].id=7;v.used.formation=false
assert(api.Read().masked.formation==1 and api.Read().rows[1].id==3735581)
api.Disable();assert(api.Snapshot(unit,{})==s and not api.Arm(0,3735581,'UNIT_MISSIONARY','owner'))
''')

    def test_legal_result_is_masked_after_real_read_and_variadic_returns_survive(self):
        self.run_lua(r'''
local before=pack(api.Qualify(unit,1592408602,1,nil,3));assert(before.n==4 and before[1]and before[3]=='native')
assert(api.Arm(0,3735581,'UNIT_MISSIONARY','legality'))
local masked=pack(api.Qualify(unit,1592408602,1,nil,3))
assert(masked.n==1 and masked[1]==nil and n.qualify==2 and n.args.n==3 and n.args[1]==1 and n.args[2]==nil and n.args[3]==3)
assert(api.Read().masked.legality==1 and api.Read().rows[1].actual_native_qualifier==true)
local other=pack(api.Qualify(unit,123,nil));assert(other.n==4 and other[1]and n.args.n==1)
api.Disable();local restored=pack(api.Qualify(unit,1592408602));assert(restored.n==4 and restored[1]and restored[3]=='native')
''')

    def test_native_nil_false_error_and_identity_failure_do_not_become_ack(self):
        self.run_lua(r'''
for _,q in ipairs({function()end,function()return nil end,function()return false end})do
 local a=Factory(snapshot,q,0,3735581,'UNIT_MISSIONARY',1592408602,64);assert(a.Arm(0,3735581,'UNIT_MISSIONARY','legality'))
 local v=pack(a.Qualify(unit,1592408602));assert(v[1]~=true and a.Read().masked.legality==0)
end
local broken=Factory(function()error('read_failed')end,qualifier,0,3735581,'UNIT_MISSIONARY',1592408602,64)
assert(broken.Arm(0,3735581,'UNIT_MISSIONARY','legality'));local v=pack(broken.Qualify(unit,1592408602));assert(v.n==4 and v[1]and broken.Read().identityErrors==1 and broken.Read().masked.legality==0)
local a=Factory(snapshot,function()error('original_qualifier_failed')end,0,3735581,'UNIT_MISSIONARY',1592408602,64)
local ok,err=pcall(a.Qualify,unit,1592408602);assert(not ok and tostring(err):find('original_qualifier_failed',1,true))
''')

    def test_three_mode_limits_expire_and_records_stay_bounded(self):
        self.run_lua(r'''
local a=Factory(snapshot,qualifier,0,3735581,'UNIT_MISSIONARY',1592408602,1)
for _,mode in ipairs({'owner','formation','legality'})do
 assert(a.Arm(0,3735581,'UNIT_MISSIONARY',mode))
 if mode=='legality'then assert(a.Qualify(unit,1592408602)==nil)else local v=a.Snapshot(unit,{});assert(v~=s)end
 local v=a.Read();assert(v.masked[mode]==1 and v.expired and not v.enabled)
 assert(a.Snapshot(unit,{})==s and not a.Arm(0,3735581,'UNIT_MISSIONARY',mode))
end
assert(#a.Read().rows==3 and a.Read().capacity==3 and a.Read().dropped==0)
''')

    def test_bad_constructor_arguments_are_rejected(self):
        self.run_lua(r'''
for _,n in ipairs({-1,2147483648,true,'0',math.huge,0/0})do
 assert(not pcall(Factory,snapshot,qualifier,n,3735581,'UNIT_MISSIONARY',1592408602,64))
end
for _,n in ipairs({0,65,true,'64',math.huge})do
 assert(not pcall(Factory,snapshot,qualifier,0,3735581,'UNIT_MISSIONARY',1592408602,n))
end
assert(not pcall(Factory,snapshot,qualifier,0,3735581,'UNIT_APOSTLE',1592408602,64))
assert(not pcall(Factory,snapshot,qualifier,0,3735581,'UNIT_MISSIONARY',123,64))
''')

    def test_actual_controller_transform_inverse_and_both_compilers(self):
        raw=(ROOT/'mod/Baiqi/Lua/BaiqiController.lua').read_text(encoding='utf-8-sig')
        changed,insertion=transform(raw,0,3735581)
        self.assertEqual(restore_release(changed,insertion),raw)
        self.assertEqual(changed.count(PRIVATE_READ),1)
        self.assertNotIn('UnitManager.CanStartOperation=',insertion)
        for VM in [Lua51,Lua53]:VM().compile(changed)
        for wrong in [raw+ANCHOR,raw.replace(ORIGINAL_READ,'return_nil'),raw+ORIGINAL_READ,changed]:
            with self.assertRaises(ValueError):transform(wrong,0,3735581)
        for owner,ident,limit in [(True,3735581,64),(0,-1,64),(0,3735581,65)]:
            with self.assertRaises(ValueError):transform(raw,owner,ident,limit)

    def test_transformed_local_bindings_restore_and_preserve_foreign_sdk_binding(self):
        raw=SNAPSHOT_SOURCE+ANCHOR+'local function Read(unit) local fresh=unit;local operation={Hash=1592408602};return '+ORIGINAL_READ+' end\nreturn function()return UnitSnapshot,Read end\n'
        changed,_=transform(raw,0,3735581)
        for VM in [Lua51,Lua53]:
            vm=VM();vm.execute("GameInfo={Units={[1]={UnitType='UNIT_MISSIONARY'}}};ActivityTypes={};UnitManager={CanStartOperation=function()return true end}")
            get=vm.execute(changed);first,read=get();api=vm.globals().P6TC040183
            self.assertTrue(api.Arm(0,3735581,'UNIT_MISSIONARY','owner')[0])
            self.assertTrue(api.Retire()[0]);restored,_=get();self.assertFalse(vm.eval('function(a,b)return a==b end')(first,restored));self.assertTrue(api.Read()['retired'])
            vm2=VM();vm2.execute("GameInfo={};ActivityTypes={};UnitManager={CanStartOperation=function()return true end}");vm2.execute(changed)
            vm2.execute('UnitManager.CanStartOperation=function()return false end');a=vm2.globals().P6TC040183
            self.assertFalse(a.Arm(0,3735581,'UNIT_MISSIONARY','owner')[0]);self.assertEqual(a.Retire(),(False,'foreign_binding_preserved'))

if __name__=='__main__':unittest.main()
