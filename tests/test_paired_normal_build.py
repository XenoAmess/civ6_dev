from pathlib import Path
from uuid import uuid4
import unittest
from lupa.lua51 import LuaRuntime
from tools.build_static_control import ROOT,build,clock_prelude


class PairedNormalBuildTests(unittest.TestCase):
    def test_both_current_variants_have_same_real_prefix_and_lua51_inventory(self):
        out=ROOT/'.local-model/paired-normal-build-tests'/uuid4().hex
        enabled=build(out/'enabled',paired_clock=True,variant='enabled',normal_end_bridge=True)
        control=build(out/'control',paired_clock=True,variant='control',normal_end_bridge=True)
        self.assertEqual(enabled['source_version'],140)
        self.assertEqual(enabled['clock_prefix_sha256'],control['clock_prefix_sha256'])
        self.assertEqual(enabled['end_bridge_sha256'],control['end_bridge_sha256'])
        for info in (enabled,control):
            self.assertEqual(info['files'],119);self.assertTrue(info['lua51_compiled'])
            self.assertTrue(info['native_activation_inline_stop'])
            self.assertFalse(info['normal_end_driver_ready'])
            self.assertFalse(info['cross_context_begin_native_verified'])
        text=(out/'enabled/Baiqi/UI/BaiqiExecutor.lua').read_text(encoding='utf-8')
        self.assertIn('local P6PairActivation=P6PairClock:WrapActivation(Activate)',text)
        self.assertIn('Events.PlayerTurnActivated.Remove(P6PairActivation)',text)

    def test_actual_prefix_publishes_bridge_and_inline_clock_stops_before_callback(self):
        lua=LuaRuntime(unpack_returned_tuples=True)
        lua.execute('''rawget=nil;rawset=nil;Clock=10;Turn=85;Callbacks={};ExposedMembers={}
Game={GetCurrentGameTurn=function()return Turn end,GetLocalPlayer=function()return 0 end}
Automation={GetTime=function()return Clock end}
Events={PlayerTurnActivated={Add=function(f)Callbacks[#Callbacks+1]=f end,
 Remove=function(f)for i,v in ipairs(Callbacks)do if v==f then table.remove(Callbacks,i);return end end end}}''')
        lua.execute(clock_prelude(normal_end_bridge=True,source_version=140))
        lua.execute('''local token=string.rep('b',32)
P6PairStage={phase='RECORDING',token=token,ends={[85]=true},normal_end=true,source_version=140}
assert(P6PairSourceVersion==140 and P6PairEndOwner.active)
local original=function(...)Clock=Clock+10;return select('#',...),...end
local alias=P6PairClock:WrapActivation(original);Events.PlayerTurnActivated.Add(alias)
Clock=50;assert(ExposedMembers.P6BaiqiPairEndBridge.Begin(85,token));Turn=86;Clock=52
for i=#Callbacks,1,-1 do Callbacks[i](0,false)end
local s=P6PairClock:Snapshot();assert(#s.records==1 and s.records[1].ended==52 and s.records[1].seconds==2)
assert(P6PairEndOwner.Retire() and ExposedMembers.P6BaiqiPairEndBridge==nil)
assert(P6PairClock:Retire());local n,a,b,c,d=alias(0,nil,false,nil)
assert(n==4 and a==0 and b==nil and c==false and d==nil)
Events.PlayerTurnActivated.Remove(alias);assert(#Callbacks==0)''')

    def test_legacy_prefix_and_unsupported_options_remain_explicit(self):
        self.assertNotIn('P6PairEndOwner',clock_prelude())
        for kwargs in ({'normal_end_bridge':True}, {'normal_end_bridge':1},
                       {'normal_end_bridge':True,'source_version':139}):
            with self.assertRaises(ValueError):clock_prelude(**kwargs)
        out=ROOT/'.local-model/paired-normal-build-tests'/uuid4().hex
        with self.assertRaises(ValueError):build(out,normal_end_bridge=True)
        self.assertFalse(out.exists())


if __name__=='__main__':
    unittest.main()
