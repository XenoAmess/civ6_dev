from pathlib import Path
import unittest
from lupa.lua51 import LuaRuntime

ROOT=Path(__file__).resolve().parents[1]


class DiagnosticQualificationTraceTests(unittest.TestCase):
    def setUp(self):
        self.lua=LuaRuntime(unpack_returned_tuples=True)
        for stem,name in [('diagnostic_qualification_trace','NewTrace'),
                          ('diagnostic_profile','NewProfile'),
                          ('diagnostic_plan_window','WrapWindow')]:
            self.lua.globals()[name]=self.lua.execute(
                (ROOT/f'tools/lua/{stem}.lua').read_text(encoding='utf-8'))
        self.lua.execute('rawget=nil;rawset=nil;H={qualificationErrors=0};Record=NewTrace(H)')

    def test_fixed_reason_buckets_and_first_sixteen_events_are_bounded(self):
        self.lua.execute('''for i=1,100 do assert(Record('foreign'..i,'Admin.Run',86,10+i)) end
local n=0;for _ in pairs(H.qualificationReasons) do n=n+1 end
assert(n==1 and H.qualificationReasons.unknown==100 and H.qualificationErrors==100)
assert(#H.qualificationEvents==16 and H.qualificationEventDropped==84)
assert(H.qualificationEvents[1].clock==11 and H.qualificationEvents[16].clock==26)''')

    def test_known_reason_counts_and_unknown_metadata_are_not_fabricated(self):
        self.lua.execute('''Record('turn','Admin.Run',86,10);Record('turn','Admin.Run',86,11)
Record('clock',{},0/0,math.huge)
assert(H.qualificationReasons.turn==2 and H.qualificationReasons.clock==1)
local e=H.qualificationEvents[3]
assert(e.label=='unknown' and e.turn==nil and e.clock==nil and e.reason=='clock')''')

    def test_saturation_and_malformed_count_remain_fail_closed(self):
        self.lua.execute('''H.qualificationErrors=2147483647
assert(Record('turn','Admin.Run',86,10) and H.qualificationErrors==2147483647 and H.qualificationSaturated)
local bad={qualificationErrors=false};local r=NewTrace(bad)
assert(r('turn','Admin.Run',86,10) and bad.qualificationErrors==2147483647)
assert(bad.qualificationTraceMalformed and bad.qualificationSaturated)
assert(not NewTrace(nil)('turn','Admin.Run',86,10))''')

    def test_hostile_metatable_and_replaced_exposed_tables_do_not_throw(self):
        self.lua.execute('''local h=setmetatable({qualificationErrors=0},{__newindex=function()error('write')end,
 __index=function()error('read')end})
local r,ready=NewTrace(h);assert(ready==false and r('turn','Admin.Run',86,10)==false)
H.qualificationReasons=false;H.qualificationEvents=false
assert(Record('player','Admin.Run',86,10) and H.qualificationTraceMalformed)
assert(H.qualificationReasons.player==1 and #H.qualificationEvents==1)''')

    def test_real_window_records_missing_anchor_without_suppressing_original(self):
        self.lua.execute('''Clock=10;Calls=0
H.enabled=true;H.anchors={};H.profile=NewProfile(function() return Clock end,4096)
H.RecordUnknown=Record
local env={Turn=function()return 86 end,LocalPlayer=function()return 0 end,
 Active=function()return true end,Now=function()return Clock end,CityCount=function()return 10 end}
local f=WrapWindow(H,'Controller.RunNow',function(...) Calls=Calls+1;return ... end,env)
local function Count(...)return select('#',...),... end
local n,a,b,c=Count(f(4,nil,false))
assert(n==3 and a==4 and b==nil and c==false and Calls==1 and H.profile.totalCalls==0)
local e=H.qualificationEvents[1]
assert(e.reason=='anchor_missing' and e.label=='Controller.RunNow' and e.turn==86 and e.clock==10)
assert(H.qualificationErrors==1)''')

    def test_suffix_unknown_is_counted_once_and_original_error_identity_survives(self):
        self.lua.execute('''Clock=10;H.enabled=true;H.anchors={[86]=10}
H.profile=NewProfile(function() return Clock end,4096);H.RecordUnknown=Record
local env={Turn=function()return 86 end,LocalPlayer=function()return 0 end,
 Active=function()return true end,Now=function()return Clock end,CityCount=function()return 10 end}
local sentinel={};local f=WrapWindow(H,'Admin.Run',function()
env.Turn=function()error('qa')end;env.CityCount=function()error('qa')end
Clock=11;error(sentinel,0) end,env)
local ok,err=pcall(f);assert(not ok and err==sentinel and H.qualificationErrors==1)
assert(H.qualificationReasons.turn_after==1 and #H.qualificationEvents==1)
assert(H.profile.samples[1].failed and H.profile.samples[1].turnEnd==nil)''')


if __name__=='__main__':
    unittest.main()
