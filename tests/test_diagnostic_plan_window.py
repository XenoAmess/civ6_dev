from pathlib import Path
import unittest
from lupa.lua51 import LuaRuntime

ROOT = Path(__file__).resolve().parents[1]


class DiagnosticPlanWindowTests(unittest.TestCase):
    def setUp(self):
        self.lua = LuaRuntime(unpack_returned_tuples=True)
        for stem, name in [('diagnostic_profile', 'NewProfile'),
                           ('diagnostic_plan_window', 'WrapWindow')]:
            self.lua.globals()[name] = self.lua.execute(
                (ROOT / f'tools/lua/{stem}.lua').read_text(encoding='utf-8'))
        self.lua.execute('''Clock=10;Turn=86;Cities=10;LP=0;Active=true;Calls=0
H={enabled=true,anchors={[86]=10,[87]=20},qualificationErrors=0,
 profile=NewProfile(function() return Clock end,4096)}
Env={Now=function() return Clock end,Turn=function() return Turn end,
 CityCount=function() return Cities end,LocalPlayer=function() return LP end,
 Active=function() return Active end}
function Body(...) Calls=Calls+1;Clock=Clock+0.02;return ... end
F=WrapWindow(H,'Admin.Run',Body,Env)''')

    def test_only_native_active_local_windows_are_timed(self):
        self.lua.execute('''H.enabled=false;F();H.enabled=true
Turn=85;F();Turn=91;F();Turn=86;LP=1;F();LP=0
Active=false;F();Active=true;Clock=20;F()
assert(Calls==6 and H.profile.totalCalls==0 and H.qualificationErrors==0)
Clock=19.999;F();assert(Calls==7 and H.profile.totalCalls==1)
local s=H.profile.samples[1];assert(s.windowEligible and s.ended>20 and s.seconds>0.019)''')

    def test_all_arguments_nil_returns_and_error_identity_survive(self):
        self.lua.execute('''local out={n=0}
local function Save(...) out={n=select('#',...),...} end
Save(F(4,nil,false,nil));assert(out.n==4 and out[1]==4 and out[2]==nil and out[3]==false and out[4]==nil)
local sentinel={};local g=WrapWindow(H,'Controller.RunNow',function(...)
 assert(select('#',...)==3 and select(3,...)==false);Clock=Clock+0.1;error(sentinel,0) end,Env)
local ok,err=pcall(g,2,nil,false);assert(not ok and err==sentinel)
local s=H.profile.samples[2];assert(s.failed and s.cityStart==10 and s.cityEnd==10)''')

    def test_distinct_rows_keep_conversion_and_full_call_duration(self):
        self.lua.execute('''F();local old=H.profile.samples[1]
Turn=87;Clock=29.99
local g=WrapWindow(H,'Admin.Run',function() Clock=31;Cities=11;Turn=88 end,Env)
g();local s=H.profile.samples[2]
assert(old.turnStart==86 and old.turnEnd==86 and old.cityEnd==10)
assert(s.turnStart==87 and s.turnEnd==88 and s.cityStart==10 and s.cityEnd==11)
assert(s.started==29.99 and s.ended==31 and s.seconds>1 and s.windowEligible)''')

    def test_unknown_prefix_getters_do_not_block_body_or_create_samples(self):
        for port in ('Turn', 'LocalPlayer', 'Active', 'Now', 'CityCount'):
            with self.subTest(port=port):
                self.setUp()
                self.lua.execute(f'''Env.{port}=function() error('qa') end
assert(F(9)==9 and Calls==1 and H.profile.totalCalls==0 and H.qualificationErrors==1)''')
        self.lua.execute('''Env.CityCount=function() return 10 end;H.anchors[86]=nil
F();assert(Calls==2 and H.qualificationErrors==2 and H.profile.totalCalls==0)''')

    def test_suffix_qa_error_cannot_mask_original_error(self):
        self.lua.execute('''local sentinel={}
local g=WrapWindow(H,'Admin.Run',function()
 Calls=Calls+1;Env.CityCount=function() error('qa-suffix') end
 Clock=Clock+0.1;error(sentinel,0) end,Env)
local ok,err=pcall(g);assert(not ok and err==sentinel and Calls==1)
local s=H.profile.samples[1]
assert(s.failed and s.cityStart==10 and s.cityEnd==nil and H.qualificationErrors==1)''')

    def test_dropped_or_invalid_clock_never_relabels_previous_row(self):
        self.lua.execute('''H.profile=NewProfile(function() return Clock end,1)
F=WrapWindow(H,'Admin.Run',Body,Env);F();local old=H.profile.samples[1]
Turn=87;Clock=20;F();assert(H.profile.dropped==1 and H.qualificationErrors==1)
assert(old.turnStart==86 and #H.profile.samples==1 and Calls==2)
local g=WrapWindow(H,'Admin.Run',function() Clock=0/0;return 5 end,Env)
assert(g()==5 and H.profile.invalidClock==1 and H.qualificationErrors==2)
assert(#H.profile.samples==1 and old.turnStart==86)''')

    def test_nested_plans_annotate_their_own_rows(self):
        self.lua.execute('''local inner=WrapWindow(H,'Controller.RunNow',Body,Env)
local outer=WrapWindow(H,'Admin.Run',function(...) inner(...);Clock=Clock+0.01;return ... end,Env)
assert(outer(3)==3 and #H.profile.samples==2)
assert(H.profile.samples[1].name=='Controller.RunNow' and H.profile.samples[1].turnStart==86)
assert(H.profile.samples[2].name=='Admin.Run' and H.profile.samples[2].turnStart==86)
assert(H.qualificationErrors==0)''')


if __name__ == '__main__':
    unittest.main()
