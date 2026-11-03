from pathlib import Path
import unittest
from lupa.lua53 import LuaRuntime
from tools.clock_offsets import intersect_offsets

ROOT=Path(__file__).resolve().parents[1]


class ClockBracketTests(unittest.TestCase):
    def setUp(self):
        self.lua=LuaRuntime(unpack_returned_tuples=True)
        self.lua.globals().Sample=self.lua.execute((ROOT/'tools/lua/diagnostic_clock_bracket.lua').read_text(encoding='utf-8'))

    def test_real_python_offset_consumer_accepts_both_offset_signs(self):
        for a,c,z,lo,hi in [(10,100,12,88,90),(100,10,102,-92,-90),(0,0,0,0,0)]:
            self.lua.execute(f'local n=0; R,E=Sample(function() n=n+1;return n==1 and {a} or {z} end,function() return {c} end)')
            g=self.lua.globals();self.assertIsNone(g.E)
            result=intersect_offsets([[g.R[i] for i in (1,2,3)]])
            self.assertEqual((result['lower_seconds'],result['upper_seconds']),(lo,hi))

    def test_bad_parameter_never_calls_either_clock(self):
        self.lua.execute('''local n=0;local f=function() n=n+1;return 1 end
for _,v in ipairs({false,'function',{},1}) do
 local r,e=Sample(v,f);assert(r==nil and e=='uiClock_param')
 r,e=Sample(f,v);assert(r==nil and e=='coreClock_param')
end
local r,e=Sample(nil,f);assert(r==nil and e=='uiClock_param')
r,e=Sample(f,nil);assert(r==nil and e=='coreClock_param' and n==0)''')

    def test_each_stage_error_stops_and_does_not_leak_stale_sample(self):
        self.lua.execute('''for stage=1,3 do
 local n=0;local clock=function() n=n+1;if n==stage then error({id=stage},0) end;return n end
 local r,e=Sample(clock,clock);assert(r==nil and e==({'ui_before_throw','core_throw','ui_after_throw'})[stage] and n==stage)
 local good,err=Sample(function() return 0 end,function() return 20 end);assert(good[2]==20 and err==nil)
end''')

    def test_non_numeric_nonfinite_and_negative_values_each_stage(self):
        self.lua.execute('''local values={false,'1',{},0/0,math.huge,-math.huge,-1}
local reasons={'type','type','type','finite','finite','finite','range'}
for i,v in ipairs(values) do for stage=1,3 do
 local n=0;local clock=function() n=n+1;if n==stage then return v end;return n end
 local r,e=Sample(clock,clock);assert(r==nil and n==stage and e==({'ui_before','core','ui_after'})[stage]..'_'..reasons[i])
end end
for stage=1,3 do local n=0;local clock=function() n=n+1;if n==stage then return nil end;return n end
 local r,e=Sample(clock,clock);assert(r==nil and n==stage and e==({'ui_before_type','core_type','ui_after_type'})[stage]) end''')

    def test_call_order_backwards_ui_and_no_global_sample_pollution(self):
        self.lua.execute('''local order={};local n=0
local r,e=Sample(function() n=n+1;order[#order+1]='UI';return n==1 and 9 or 8 end,function() order[#order+1]='Core';return 100 end)
assert(r==nil and e=='order' and table.concat(order,',')=='UI,Core,UI')''')
        other=LuaRuntime();fn=other.execute((ROOT/'tools/lua/diagnostic_clock_bracket.lua').read_text(encoding='utf-8'))
        self.assertIsNotNone(fn);self.assertIsNone(other.globals().Sample)


if __name__=='__main__':
    unittest.main()
