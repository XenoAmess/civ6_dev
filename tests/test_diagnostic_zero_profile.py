from pathlib import Path
import unittest
from lupa.lua53 import LuaRuntime

ROOT=Path(__file__).resolve().parents[1]


class ZeroProfileTests(unittest.TestCase):
    def setUp(self):
        self.lua=LuaRuntime(unpack_returned_tuples=True)
        self.lua.execute('unpack=table.unpack;table.unpack=nil;table.pack=nil')
        self.lua.globals().New=self.lua.execute((ROOT/'tools/lua/diagnostic_profile.lua').read_text(encoding='utf-8'))

    def test_zero_success_aggregation_keeps_exact_calls_and_tail_returns(self):
        self.lua.execute('''local p=New(function() return 1 end,1,{aggregate_zero=true})
local calls=0;local f=p:Wrap('zero',function(...) calls=calls+1;return select('#',...),... end)
local function Pack(...) return {n=select('#',...),...} end
for i=1,1000 do local r=Pack(f(1,nil,false,nil));assert(r.n==5 and r[1]==4 and r[4]==false and r[5]==nil) end
assert(calls==1000 and p.totalCalls==1000 and p.zeroSuccess==1000 and #p.samples==0 and p.dropped==0 and p.invalidClock==0)
assert(p.totalCalls==#p.samples+p.zeroSuccess+p.dropped+p.invalidClock)''')

    def test_default_and_explicit_false_keep_old_zero_sample_behavior(self):
        self.lua.execute('''for _,options in ipairs({{}, {aggregate_zero=false}}) do
 local p=New(function() return 1 end,2,options);local f=p:Wrap('zero',function() return false end)
 for i=1,3 do assert(f()==false) end
 assert(not p.aggregateZero and p.zeroSuccess==0 and #p.samples==2 and p.dropped==1 and p.totalCalls==3)
end
local p=New(function() return 1 end,1);p:Wrap('z',function() end)()
assert(#p.samples==1 and p.zeroSuccess==0 and not p.aggregateZero)''')

    def test_small_positive_duration_is_never_rounded_to_zero(self):
        self.lua.execute('''local n=0;local p=New(function() n=n+1;return n==1 and 0 or 1e-12 end,1,{aggregate_zero=true})
p:Wrap('tiny',function() return 7 end)()
assert(#p.samples==1 and p.samples[1].seconds==1e-12 and p.zeroSuccess==0)''')

    def test_failed_zero_retained_or_dropped_with_original_error_object(self):
        self.lua.execute('''local p=New(function() return 1 end,1,{aggregate_zero=true});local E={}
local f=p:Wrap('failed-zero',function() error(E,0) end)
for i=1,2 do local ok,e=pcall(f);assert(not ok and e==E) end
assert(#p.samples==1 and p.samples[1].failed and p.samples[1].seconds==0 and p.dropped==1 and p.zeroSuccess==0)
assert(p.totalCalls==#p.samples+p.zeroSuccess+p.dropped+p.invalidClock)''')

    def test_invalid_and_backwards_clock_never_aggregate_or_skip_body(self):
        self.lua.execute('''local calls=0;local p=New(function() error('clock') end,1,{aggregate_zero=true})
assert(p:Wrap('body',function() calls=calls+1;return 9 end)()==9 and calls==1)
assert(p.invalidClock==1 and p.zeroSuccess==0 and #p.samples==0)
local n=0;p=New(function() n=n+1;return n==1 and 2 or 1 end,1,{aggregate_zero=true})
p:Wrap('backwards',function() calls=calls+1 end)()
assert(p.invalidClock==1 and p.zeroSuccess==0 and #p.samples==0 and calls==2)''')

    def test_options_validation_includes_boolean_false(self):
        self.lua.execute('''for _,value in ipairs({false,true,1,'options'}) do
assert(not pcall(function() New(function() return 1 end,1,value) end)) end
for _,value in ipairs({1,'true'}) do assert(not pcall(function() New(nil,1,{aggregate_zero=value}) end)) end
assert(pcall(function() New(nil,1,nil) end))''')


if __name__=='__main__':unittest.main()
