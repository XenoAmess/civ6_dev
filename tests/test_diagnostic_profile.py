"""Protect native callback semantics before external profiling is allowed."""
from pathlib import Path
import unittest
from lupa.lua53 import LuaRuntime

SOURCE = Path(__file__).resolve().parents[1] / "tools/lua/diagnostic_profile.lua"


class DiagnosticProfileTests(unittest.TestCase):
    def setUp(self):
        self.lua = LuaRuntime(unpack_returned_tuples=True)
        self.lua.execute("""
unpack=table.unpack;table.unpack=nil;table.pack=nil;debug=nil
function Pack(...) return {n=select('#',...),...} end
function Clock() ticks=ticks+1;return ticks/1000 end
ticks=0;calls=0
""")
        self.lua.globals().NewProfile = self.lua.execute(SOURCE.read_text(encoding="utf-8"))

    def check_lua(self, code):
        self.lua.execute(code)

    def test_all_arguments_and_returns_include_nil_holes_and_trailing_nil(self):
        self.check_lua("""
local s=NewProfile(Clock,4)
local f=s:Wrap('native',function(...)
 calls=calls+1;local a=Pack(...)
 assert(a.n==15 and a[1]==false and a[3]==nil and a[14]==14 and a[15]==nil)
 return false,2,nil,4,5,6,7,8,9,10,11,12,nil,14,nil
end)
local r=Pack(f(false,2,nil,4,5,6,7,8,9,10,11,12,nil,14,nil))
assert(r.n==15 and r[1]==false and r[2]==2 and r[3]==nil and r[14]==14 and r[15]==nil)
assert(calls==1 and s.totalCalls==1 and #s.samples==1 and not s.samples[1].failed)
""")

    def test_false_allow_orders_reaches_original_once(self):
        self.check_lua("""
local s=NewProfile(Clock,2)
local f=s:Wrap('RunNow',function(allowOrders)
 calls=calls+1;assert(allowOrders==false);return 'held'
end)
assert(f(false)=='held' and calls==1)
""")

    def test_no_return_remains_zero_return_values(self):
        self.check_lua("""
local s=NewProfile(Clock,2)
local f=s:Wrap('empty',function() calls=calls+1 end)
assert(Pack(f()).n==0 and calls==1)
""")

    def test_original_error_identity_and_failure_sample_are_preserved(self):
        self.check_lua("""
local s=NewProfile(Clock,2);local originalError={}
local f=s:Wrap('bad',function() calls=calls+1;error(originalError,0) end)
local ok,err=pcall(f)
assert(not ok and err==originalError and calls==1)
assert(s.totalCalls==1 and #s.samples==1 and s.samples[1].failed==true)
""")

    def test_clock_failure_never_suppresses_original_or_fabricates_duration(self):
        self.check_lua("""
for _,clock in ipairs({
 function() error('clock failure') end,
 function() return 'not a number' end,
 function() return 0/0 end,
 function() return math.huge end,
 function() return -math.huge end
}) do
 local s=NewProfile(clock,2)
 local before=calls;local f=s:Wrap('native',function() calls=calls+1;return false,nil,'ok' end)
 local r=Pack(f())
 assert(r.n==3 and r[1]==false and r[3]=='ok' and calls==before+1)
 assert(s.invalidClock==1 and #s.samples==0 and s.dropped==0)
end
""")

    def test_missing_clock_and_invalid_end_are_counted_once_per_interval(self):
        self.check_lua("""
local s=NewProfile(nil,2);local f=s:Wrap('native',function() calls=calls+1;return 9 end)
assert(f()==9 and s.invalidClock==1 and calls==1)
local reads=0
local other=NewProfile(function() reads=reads+1;if reads==1 then return 1 end end,2)
assert(other:Wrap('native',function() calls=calls+1;return 10 end)()==10)
assert(other.invalidClock==1 and #other.samples==0 and calls==2)
""")

    def test_backwards_or_overflowing_interval_is_invalid(self):
        self.check_lua("""
for _,values in ipairs({{2,1},{-1e308,1e308}}) do
 local reads=0;local s=NewProfile(function() reads=reads+1;return values[reads] end,2)
 local before=calls
 assert(s:Wrap('native',function() calls=calls+1;return 'ok' end)()=='ok')
 assert(calls==before+1 and s.invalidClock==1 and #s.samples==0)
end
""")

    def test_capacity_bounds_storage_without_dropping_original_calls(self):
        self.check_lua("""
local s=NewProfile(Clock,2)
local f=s:Wrap('native',function(value) calls=calls+1;return value end)
for i=1,7 do assert(f(i)==i) end
assert(calls==7 and s.totalCalls==7 and #s.samples==2 and s.dropped==5 and s.invalidClock==0)
assert(s.samples[1].seconds>0 and s.samples[2].name=='native')
""")

    def test_invalid_capacity_is_rejected_before_installation(self):
        self.check_lua("""
for _,cap in ipairs({false,'2',0,-1,1.5,math.huge,-math.huge,0/0}) do
 local ok=pcall(NewProfile,Clock,cap);assert(not ok)
end
assert(not pcall(NewProfile,Clock,nil))
assert(calls==0)
""")

    def test_nested_wrappers_preserve_their_inclusive_scope_and_returns(self):
        self.check_lua("""
local s=NewProfile(Clock,4)
local inner=s:Wrap('inner',function() calls=calls+1;return nil,false end)
local outer=s:Wrap('outer',function() return inner() end)
local r=Pack(outer())
assert(r.n==2 and r[1]==nil and r[2]==false and calls==1)
assert(s.totalCalls==2 and #s.samples==2)
assert(s.samples[1].name=='inner' and s.samples[2].name=='outer')
assert(s.samples[2].seconds>s.samples[1].seconds)
""")


if __name__ == "__main__":
    unittest.main()
