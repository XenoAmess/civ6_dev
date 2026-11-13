from pathlib import Path
import unittest
from lupa.lua51 import LuaRuntime

ROOT=Path(__file__).resolve().parents[1]


class DiagnosticPreanchorProofTests(unittest.TestCase):
    def setUp(self):
        self.lua=LuaRuntime(unpack_returned_tuples=True)
        for stem,name in [('diagnostic_profile','NewProfile'),('diagnostic_preanchor_proof','NewDeferred')]:
            self.lua.globals()[name]=self.lua.execute((ROOT/f'tools/lua/{stem}.lua').read_text(encoding='utf-8'))
        self.lua.execute('''rawget=nil;rawset=nil;Clock=1;Unknowns=0
P=NewProfile(function()return Clock end,4096);A={}
S=NewDeferred(P,A,function()Unknowns=Unknowns+1 end)
function Row(turn)
 local f=P:Wrap('Controller.RunNow',function()Clock=Clock+1 end);f()
 local r=P.samples[#P.samples];r.turnStart=turn;r.turnEnd=turn;r.cityStart=10;r.cityEnd=10
 r.preAnchor=true;r.argumentCount=1;r.allowOrders='false';return r
end''')

    def test_actual_canonical_row_stays_pending_until_exact_native_anchor(self):
        self.lua.execute('''local r=Row(86);assert(S:Record(r,86))
assert(S.pending==1 and S.recorded==1 and S.validated==0 and r.anchor==nil)
A[86]=10;assert(S:Resolve(86,10))
assert(S.pending==0 and S.recorded==1 and S.validated==1 and S.errors==0)
assert(r.anchor==10 and r.windowEligible==false and P.totalCalls==1 and #P.samples==1)
assert(S:Resolve(86,10)and S.validated==1 and Unknowns==0)''')

    def test_already_known_anchor_and_reentrant_overlap_take_distinct_paths(self):
        self.lua.execute('''A[86]=10;local r=Row(86);assert(S:Record(r,86))
assert(S.pending==0 and S.validated==1 and r.anchor==10)
Clock=19;local crossing=Row(87);Clock=21;crossing.ended=21;A[87]=20
assert(not S:Record(crossing,87)and S.pending==0 and S.errors==1 and S.validated==1)
assert(crossing.anchor==20 and #P.samples==2 and Unknowns==1)''')

    def test_duplicate_and_noncanonical_row_cannot_inflate_or_silently_succeed(self):
        self.lua.execute('''local r=Row(86);assert(S:Record(r,86))
assert(not S:Record(r,86)and S.recorded==1 and S.pending==1 and S.errors==1)
local fake={name='Controller.RunNow',preAnchor=true,argumentCount=1,allowOrders='false'}
assert(not S:Record(fake,86)and S.recorded==1 and S.errors==2)''')

    def test_bad_clock_metadata_or_failed_call_never_qualifies(self):
        for edit in ('r.started=9;r.ended=8','r.started=0/0','r.cityEnd=-1',
                     'r.turnEnd=87','r.failed=true','r.started=10;r.ended=10'):
            with self.subTest(edit=edit):
                self.setUp()
                self.lua.execute('local r=Row(86);'+edit+'''
assert(S:Record(r,86));A[86]=10;assert(not S:Resolve(86,10))
assert(S.validated==0 and S.errors==1 and Unknowns==1 and #P.samples==1)''')

    def test_missing_anchor_remains_pending_and_forged_resolution_is_unknown(self):
        self.lua.execute('''local r=Row(86);assert(S:Record(r,86))
assert(S.pending==1 and S.validated==0)
assert(not S:Resolve(86,10)and S.pending==1 and S.errors==1)
A[86]=10;assert(not S:Resolve(86,11)and S.pending==1 and S.errors==2)''')

    def test_only_exact_false_single_argument_controller_call_can_be_recorded(self):
        for edit in ("r.name='Admin.Run'","r.allowOrders='true'","r.allowOrders='nil'",'r.argumentCount=0'):
            with self.subTest(edit=edit):
                self.setUp();self.lua.execute('local r=Row(86);'+edit+'''
assert(not S:Record(r,86)and S.recorded==0 and S.pending==0 and S.errors==1)''')

    def test_global_capacity_and_throwing_unknown_sink_are_bounded(self):
        self.lua.execute('''P=NewProfile(function()return Clock end,1)
S=NewDeferred(P,A,function()Unknowns=Unknowns+1 end)
local r=Row(86);assert(S:Record(r,86))
-- A forged extra producer row cannot enlarge the proof queue past capacity.
local second={name='Controller.RunNow',preAnchor=true,argumentCount=1,allowOrders='false'}
P.samples[2]=second;assert(not S:Record(second,87))
assert(S.recorded==1 and S.pending==1 and S.errors==1)
local bad=NewDeferred(P,A,function()error('qa-sink')end)
local ok,v=pcall(function()return bad:Record({},86)end)
assert(ok and v==false and bad.errors==1)''')


if __name__=='__main__':
    unittest.main()
