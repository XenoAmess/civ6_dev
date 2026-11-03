from pathlib import Path
import unittest
from lupa.lua53 import LuaRuntime

ROOT=Path(__file__).resolve().parents[1]


class OwnedRootTests(unittest.TestCase):
    def setUp(self):
        self.lua=LuaRuntime(unpack_returned_tuples=True)
        self.lua.execute('unpack=table.unpack;table.unpack=nil;table.pack=nil')
        for name,key in [('diagnostic_profile','NewProfile'),('diagnostic_owned_roots','New')]:
            self.lua.globals()[key]=self.lua.execute((ROOT/f'tools/lua/{name}.lua').read_text(encoding='utf-8'))
        self.lua.execute('ClockCalls=0;local function Clock() ClockCalls=ClockCalls+1;return ClockCalls end;H=New(NewProfile,Clock,4);assert(ClockCalls==0)')

    def test_disabled_and_nested_have_no_additional_profile_or_clock_calls(self):
        self.lua.execute('''local n=0
local inner=H:Wrap('inner',function(...) n=n+1;return ... end)
local outer=H:Wrap('outer',function(...) return inner(...) end)
outer(1);assert(ClockCalls==0 and H.profile.totalCalls==0 and n==1)
H:SetEnabled(true);local a,b,c=outer(1,nil,false)
assert(a==1 and b==nil and c==false and n==2 and H.profile.totalCalls==1 and ClockCalls==2 and H.profile.samples[1].name=='outer')''')

    def test_original_error_object_and_unwind_after_failure(self):
        self.lua.execute('''local E={};local boom=H:Wrap('boom',function() error(E,0) end)
H:SetEnabled(true);local ok,e=pcall(boom);assert(not ok and e==E)
local good=H:Wrap('good',function() return 9 end);assert(good()==9)
assert(H.profile.totalCalls==2 and H.profile.samples[1].failed and not H.profile.samples[2].failed)''')

    def test_caught_nested_failure_and_reentry_still_only_one_root(self):
        self.lua.execute('''local E={};local boom=H:Wrap('boom',function() error(E,0) end)
local recurse;recurse=H:Wrap('recursive',function(n) if n>0 then return recurse(n-1) end;local ok,e=pcall(boom);assert(not ok and e==E);return 5 end)
H:SetEnabled(true);assert(recurse(3)==5 and H.profile.totalCalls==1 and not H.profile.samples[1].failed)''')

    def test_disable_reenable_inside_active_call_does_not_leak_depth(self):
        self.lua.execute('''local inner=H:Wrap('inner',function() return 3 end)
local outer=H:Wrap('outer',function() H:SetEnabled(false);assert(inner()==3);H:SetEnabled(true);return inner() end)
H:SetEnabled(true);assert(outer()==3 and inner()==3 and H.profile.totalCalls==2)
H:SetEnabled(false);inner();assert(H.profile.totalCalls==2)''')

    def test_tail_nil_exact_arity_no_constructor_or_control_invocations(self):
        self.lua.execute('''local calls=0;local f=H:Wrap('f',function(...) calls=calls+1;return select('#',...),... end)
assert(calls==0 and ClockCalls==0);H:SetEnabled(true);assert(calls==0 and ClockCalls==0)
local function Pack(...) return {n=select('#',...),...} end
local a=Pack(f(1,nil,false,nil));assert(a.n==5 and a[1]==4 and a[4]==false and a[5]==nil and calls==1)
assert(not pcall(function() H:SetEnabled(1) end) and not pcall(function() H:Wrap('bad',nil) end))''')

    def test_canonical_capacity_overflow_and_clock_failure_remain_visible(self):
        self.lua.execute('''H:SetEnabled(true);local f=H:Wrap('f',function() return 1 end)
for i=1,6 do assert(f()==1) end
assert(H.profile.totalCalls==6 and #H.profile.samples==4 and H.profile.dropped==2)
local bad=New(NewProfile,function() error('clock') end,2);bad:SetEnabled(true)
assert(bad:Wrap('g',function() return 7 end)()==7 and bad.profile.invalidClock==1)''')


if __name__=='__main__':unittest.main()
