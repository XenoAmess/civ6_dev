from pathlib import Path
import unittest
from lupa.lua53 import LuaRuntime

ROOT = Path(__file__).resolve().parents[1]
CHILD_SOURCE = ROOT / 'tools/lua/diagnostic_child_profile.lua'


class ChildProfileTests(unittest.TestCase):
    def setUp(self):
        self.lua = LuaRuntime(unpack_returned_tuples=True)
        self.lua.execute('''
unpack=table.unpack;table.unpack=nil;table.pack=nil;debug=nil
function Pack(...) return {n=select('#',...),...} end
ticks=0;calls=0
function Clock() ticks=ticks+1;return ticks/1000 end
root={id=7,turnBefore=86,citiesBefore=10}
function GetRoot() return root end
''')
        self.lua.globals().NewProfile = self.lua.execute(
            (ROOT / 'tools/lua/diagnostic_profile.lua').read_text(encoding='utf-8'))
        self.lua.globals().WrapChild = self.lua.execute(CHILD_SOURCE.read_text(encoding='utf-8'))

    def test_outside_root_bypasses_clock_and_keeps_nil_returns(self):
        self.lua.execute('''
local s=NewProfile(Clock,4);root=nil
local f=WrapChild(s,'work',function() calls=calls+1;return false,nil end,GetRoot)
local r=Pack(f());assert(calls==1 and r.n==2 and r[1]==false and s.totalCalls==0 and ticks==0)
''')

    def test_root_getter_failure_fails_open_and_counts_metadata(self):
        self.lua.execute('''
local s=NewProfile(Clock,4)
local f=WrapChild(s,'work',function() calls=calls+1;return 8 end,function() error('metadata') end)
assert(f()==8 and calls==1 and s.metadataErrors==1 and s.totalCalls==0)
''')

    def test_arguments_returns_and_root_identity(self):
        self.lua.execute('''
local s=NewProfile(Clock,4)
local f=WrapChild(s,'work',function(...)
 local a=Pack(...);assert(a.n==4 and a[1]==false and a[2]==nil and a[3]==9 and a[4]==nil)
 calls=calls+1;return false,nil,9,nil
end,GetRoot)
local r=Pack(f(false,nil,9,nil));assert(r.n==4 and r[1]==false and r[3]==9 and calls==1)
local sample=s.samples[1];assert(sample.rootId==7 and sample.rootTurn==86 and sample.rootCities==10)
''')

    def test_root_fields_are_captured_before_original_mutates_them(self):
        self.lua.execute('''
local s=NewProfile(Clock,4)
WrapChild(s,'work',function() calls=calls+1;root.id=9;root.turnBefore=87;root.citiesBefore=11 end,GetRoot)()
local sample=s.samples[1];assert(calls==1 and sample.rootId==7 and sample.rootTurn==86 and sample.rootCities==10)
''')

    def test_original_error_identity_and_failed_sample_annotation(self):
        self.lua.execute('''
local s=NewProfile(Clock,4);local token={}
local ok,err=pcall(WrapChild(s,'work',function() calls=calls+1;error(token,0) end,GetRoot))
assert(not ok and err==token and calls==1 and s.samples[1].failed and s.samples[1].rootId==7)
''')

    def test_capacity_drop_does_not_retag_inner_same_name(self):
        self.lua.execute('''
local s=NewProfile(Clock,1)
local inner=WrapChild(s,'same',function() calls=calls+1;return 8 end,GetRoot)
local outer=WrapChild(s,'same',function()
 root={id=9,turnBefore=87,citiesBefore=11};return inner()
end,GetRoot)
assert(outer()==8 and calls==1 and s.dropped==1 and s.samples[1].rootId==9)
''')

    def test_invalid_outer_clock_does_not_retag_inner_same_name(self):
        self.lua.execute('''
local reads=0;local s=NewProfile(function() reads=reads+1;if reads==4 then return 0/0 end;return reads end,4)
local inner=WrapChild(s,'same',function() calls=calls+1;return 8 end,GetRoot)
local outer=WrapChild(s,'same',function()
 root={id=9,turnBefore=87,citiesBefore=11};return inner()
end,GetRoot)
assert(outer()==8 and calls==1 and s.invalidClock==1 and #s.samples==1 and s.samples[1].rootId==9)
''')

    def test_valid_nested_samples_keep_their_own_roots(self):
        self.lua.execute('''
local s=NewProfile(Clock,4)
local inner=WrapChild(s,'inner',function() calls=calls+1;return nil,false end,GetRoot)
local outer=WrapChild(s,'outer',function() root={id=9,turnBefore=87,citiesBefore=11};return inner() end,GetRoot)
local r=Pack(outer());assert(r.n==2 and r[1]==nil and r[2]==false and calls==1)
assert(s.samples[1].rootId==9 and s.samples[2].rootId==7)
''')

    def test_zero_return_values_remain_zero(self):
        self.lua.execute('''
local s=NewProfile(Clock,2)
assert(Pack(WrapChild(s,'work',function() calls=calls+1 end,GetRoot)()).n==0 and calls==1)
''')

    def test_invalid_target_rejected_before_execution(self):
        self.lua.execute('''
local s=NewProfile(Clock,2)
assert(not pcall(WrapChild,s,'work',nil,GetRoot) and calls==0)
''')
