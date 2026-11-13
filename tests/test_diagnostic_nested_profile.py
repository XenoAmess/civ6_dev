from pathlib import Path
import unittest
from lupa.lua51 import LuaRuntime

ROOT=Path(__file__).resolve().parents[1]


class NestedProfileTests(unittest.TestCase):
    candidate_source=None

    def setUp(self):
        self.lua=LuaRuntime(unpack_returned_tuples=True)
        self.lua.execute('rawget=nil;rawset=nil;debug=nil')
        for var,name in (('NewProfile','diagnostic_profile'),('WrapChild','diagnostic_child_profile')):
            self.lua.globals()[var]=self.lua.execute((ROOT/f'tools/lua/{name}.lua').read_text(encoding='utf-8'))
        source=self.candidate_source
        if source is None:source=(ROOT/'tools/lua/diagnostic_nested_profile.lua').read_text(encoding='utf-8')
        self.lua.globals().NewNested=self.lua.execute(source)
        self.lua.execute('''
T={time=100,reads=0,bodies=0}
function Now()T.reads=T.reads+1;T.time=T.time+.001;return T.time end
function Qualify()return{turnBefore=88,citiesBefore=10}end
h=NewNested(NewProfile,WrapChild,Now,Qualify)
''')

    def test_disabled_and_outside_focus_preserve_all_arguments_and_returns(self):
        self.lua.execute('''
local fn=h.WrapRoot(function(...)T.bodies=T.bodies+1;assert(select('#',...)==3);local a,b,c=...;assert(a==false and b==nil and c==9);return false,nil,9,nil end)
local function check(...)assert(select('#',...)==4);local a,b,c,d=...;assert(a==false and b==nil and c==9 and d==nil)end
check(fn(false,nil,9));assert(T.bodies==1 and h.profile.totalCalls==0)
h.SetEnabled(true);Qualify=function()return nil end
-- The supplied port is captured by constructor, so use a fresh owner for nil focus.
h=NewNested(NewProfile,WrapChild,Now,Qualify);h.SetEnabled(true)
fn=h.WrapRoot(function(...)T.bodies=T.bodies+1;assert(select('#',...)==3);return false,nil,9,nil end)
check(fn(false,nil,9))
assert(h.profile.totalCalls==0 and T.bodies==2 and h.currentEntry==nil)
''')

    def test_two_roots_have_unique_ids_and_correlated_children(self):
        self.lua.execute('''
local child=h.WrapChild('ReadBack',function(v)return v,nil end)
local root=h.WrapRoot(function(v)T.bodies=T.bodies+1;return child(v)end)
h.SetEnabled(true);root(false);root(true)
assert(h.serial==2 and #h.profile.samples==4 and h.profile.totalCalls==4)
for i,r in ipairs(h.profile.samples)do assert(r.rootId==math.ceil(i/2)and r.rootTurn==88 and r.rootCities==10)end
assert(h.currentEntry==nil and h.errors==0)
''')

    def test_throwing_qualifier_does_not_block_body(self):
        self.lua.execute('''
local a=NewNested(NewProfile,WrapChild,Now,function()error('metadata')end)
a.SetEnabled(true);local fn=a.WrapRoot(function()T.bodies=T.bodies+1;return false,nil end)
local x,y=fn();assert(x==false and y==nil and T.bodies==1 and a.errors==1 and a.profile.totalCalls==0)
''')

    def test_snapshot_bounds_are_strict(self):
        self.lua.execute('''
for _,bad in ipairs({true,-1,.5,2147483648,math.huge})do
 for _,key in ipairs({'turnBefore','citiesBefore'})do
  local a=NewNested(NewProfile,WrapChild,Now,function()local s={turnBefore=88,citiesBefore=10};s[key]=bad;return s end)
  a.SetEnabled(true);local before=T.bodies
  a.WrapRoot(function()T.bodies=T.bodies+1 end)()
  assert(T.bodies==before+1 and a.errors==1 and #a.profile.samples==0 and a.currentEntry==nil)
 end
end
''')

    def test_snapshot_getter_failure_does_not_block_body(self):
        self.lua.execute('''
local a=NewNested(NewProfile,WrapChild,Now,function()return setmetatable({},{__index=function()error('snapshot read')end})end)
a.SetEnabled(true);local ok=pcall(a.WrapRoot(function()T.bodies=T.bodies+1 end))
assert(ok and T.bodies==1 and a.errors==1 and a.currentEntry==nil)
''')

    def test_error_identity_and_nil_returns_leave_no_root(self):
        self.lua.execute('''
h.SetEnabled(true);local boom={}
local child=h.WrapChild('ProcessCity',function(...)assert(select('#',...)==2);error(boom,0)end)
local root=h.WrapRoot(function(...)return child(...)end)
local ok,err=pcall(root,false,nil);assert(not ok and err==boom and h.currentEntry==nil)
assert(#h.profile.samples==2 and h.profile.samples[1].failed and h.profile.samples[2].failed)
''')

    def test_reentrant_root_forwards_without_second_measurement(self):
        self.lua.execute('''
h.SetEnabled(true);local root
root=h.WrapRoot(function(n)T.bodies=T.bodies+1;if n==1 then return root(0)end;return false,nil end)
local a,b=root(1);assert(a==false and b==nil and T.bodies==2 and #h.profile.samples==1 and h.currentEntry==nil)
''')

    def test_invalid_outer_clock_never_relabels_last_child(self):
        self.lua.execute('''
local reads=0
local a=NewNested(NewProfile,WrapChild,function()reads=reads+1;if reads==1 then error('clock')end;return reads end,Qualify)
a.SetEnabled(true);local child=a.WrapChild('ReadBack',function()return false end)
a.WrapRoot(function()return child()end)()
assert(#a.profile.samples==1 and a.profile.samples[1].name=='ReadBack')
assert(a.profile.invalidClock==1 and a.errors==1 and a.currentEntry==nil)
''')

    def test_root_and_children_share_total4096_budget(self):
        self.lua.execute('''
h.SetEnabled(true);local child=h.WrapChild('ReadBack',function()end)
local root=h.WrapRoot(function()child()end)
for i=1,2050 do root()end
assert(#h.profile.samples==4096 and h.profile.totalCalls==4100 and h.profile.dropped==4 and h.errors>0)
assert(h.currentEntry==nil)
''')

    def test_child_outside_root_and_reserved_label(self):
        self.lua.execute('''
local child=h.WrapChild('ReadBack',function()T.bodies=T.bodies+1;return false,nil end)
h.SetEnabled(true);child();assert(T.bodies==1 and #h.profile.samples==0)
local ok=pcall(h.WrapChild,'Controller.RunNow',function()end);assert(not ok)
h.errors=1;h.SetEnabled(false);h.SetEnabled(true);assert(h.enabled==false)
''')


if __name__=='__main__':unittest.main()
