from pathlib import Path
import unittest
from lupa.lua53 import LuaRuntime

ROOT = Path(__file__).resolve().parents[1]
DUAL_SOURCE = ROOT / 'tools/lua/diagnostic_dual_profile.lua'


class DualProfileTests(unittest.TestCase):
    def setUp(self):
        self.lua = LuaRuntime(unpack_returned_tuples=True)
        self.lua.execute('''
unpack=table.unpack;table.unpack=nil;table.pack=nil;debug=nil
function Pack(...) return {n=select('#',...),...} end
w=0;c=0;calls=0;trace=''
function Wall() w=w+1;trace=trace..'W';return w/100 end
function CPU() c=c+1;trace=trace..'C';return c/1000 end
''')
        self.lua.globals().NewProfile = self.lua.execute(
            (ROOT / 'tools/lua/diagnostic_profile.lua').read_text(encoding='utf-8'))
        self.lua.globals().NewDual = self.lua.execute(DUAL_SOURCE.read_text(encoding='utf-8'))

    def test_clock_order_and_exactly_one_original_call(self):
        self.lua.execute('''
local d=NewDual(NewProfile,Wall,CPU,4)
local f=d:Wrap('work',function() calls=calls+1;trace=trace..'F';return 7 end)
assert(f()==7 and calls==1 and trace=='WCFCW')
assert(#d.wall.samples==1 and #d.cpu.samples==1)
assert(d.wall.samples[1].seconds>d.cpu.samples[1].seconds)
''')

    def test_nil_holes_false_and_trailing_nil(self):
        self.lua.execute('''
local d=NewDual(NewProfile,Wall,CPU,4)
local f=d:Wrap('work',function(...)
 calls=calls+1;local a=Pack(...);assert(a.n==4 and a[1]==false and a[2]==nil and a[3]==9 and a[4]==nil)
 return false,nil,9,nil
end)
local r=Pack(f(false,nil,9,nil));assert(r.n==4 and r[1]==false and r[2]==nil and r[3]==9 and r[4]==nil and calls==1)
''')

    def test_allow_orders_false_reaches_original(self):
        self.lua.execute('''
local d=NewDual(NewProfile,Wall,CPU,2)
local f=d:Wrap('work',function(allow) assert(allow==false);calls=calls+1;return false end)
assert(f(false)==false and calls==1)
''')

    def test_zero_returns(self):
        self.lua.execute('''
local d=NewDual(NewProfile,Wall,CPU,2)
local r=Pack(d:Wrap('work',function() calls=calls+1 end)())
assert(r.n==0 and calls==1)
''')

    def test_error_identity_and_both_failure_samples(self):
        self.lua.execute('''
local d=NewDual(NewProfile,Wall,CPU,2);local token={}
local ok,err=pcall(d:Wrap('work',function() calls=calls+1;error(token,0) end))
assert(not ok and err==token and calls==1)
assert(d.wall.samples[1].failed and d.cpu.samples[1].failed)
''')

    def test_one_bad_clock_does_not_suppress_work_or_other_clock(self):
        self.lua.execute('''
local d=NewDual(NewProfile,Wall,function() error('clock') end,2)
assert(d:Wrap('work',function() calls=calls+1;return 8 end)()==8)
assert(calls==1 and d.cpu.invalidClock==1 and #d.cpu.samples==0 and #d.wall.samples==1)
''')

    def test_bounded_capacity_keeps_all_original_calls(self):
        self.lua.execute('''
local d=NewDual(NewProfile,Wall,CPU,2)
local f=d:Wrap('work',function(i) calls=calls+1;return i end)
for i=1,7 do assert(f(i)==i) end
assert(calls==7 and d.wall.totalCalls==7 and d.cpu.totalCalls==7)
assert(#d.wall.samples==2 and #d.cpu.samples==2 and d.wall.dropped==5 and d.cpu.dropped==5)
''')

    def test_invalid_capacity_rejected_before_original(self):
        self.lua.execute('''
assert(not pcall(NewDual,NewProfile,Wall,CPU,0) and calls==0)
''')
