from pathlib import Path
import unittest
import test_diagnostic_plan_stage as fixture

ROOT=Path(__file__).resolve().parents[1]


class PressureCalendarTests(unittest.TestCase):
    def setUp(self):
        self.case=fixture.DiagnosticPlanStageTests();self.case.setUp();self.lua=self.case.lua
        self.lua.globals().NewDeferred=self.lua.execute((ROOT/'tools/lua/diagnostic_preanchor_proof.lua').read_text(encoding='utf-8'))
        self.lua.execute('function Make(t)H=NewPlanA(Env,NewProfile,WrapWindow,NewTrace,NewDeferred,142,t);assert(H.Bind(Admin,Controller)and H.SetEnabled(true))end')

    def test_zero_210_and_maximum_keep_actual_anchors_and_five_windows(self):
        for t in (0,210,2147483641):
            with self.subTest(t=t):
                self.setUp();self.lua.globals().T=t
                self.lua.execute('''Make(T);assert(H.source=='baiqi142-pressure-stageA-v1'and H.initialTurn==T)
Turn=T-1;Fire(0);assert(H.anchorCount==0)
Turn=T;Fire(0);assert(H.anchors[T]==10)
Turn=T+1;Clock=20;Fire(0);Controller.RunNow()
assert(H.anchors[T+1]==20 and #H.profile.samples==1 and H.profile.samples[1].turnStart==T+1)
Clock=25;Fire(0);assert(H.anchors[T+1]==20)
Turn=T+5;Clock=100;Fire(0);Admin.Run()
Turn=T+6;Clock=110;Fire(0);Admin.Run()
Turn=T+7;Fire(0);assert(H.anchors[T+6]==110 and H.anchors[T+7]==nil)
assert(#H.profile.samples==2 and H.profile.capacity==4096 and not H.profile.aggregateZero and H.qualificationErrors==0)
''')

    def test_legacy_noarg_calls_and_preanchor_factory_arity_remain_valid(self):
        self.lua.execute('''local arity;local real=NewDeferred
local function spy(...)arity=select('#',...);return real(...)end
H=NewPlanA(Env,NewProfile,WrapWindow,NewTrace,spy)
assert(arity==3 and H.initialTurn==nil and H.source=='baiqi140-stageA-v2')
assert(H.Bind(Admin,Controller)and H.SetEnabled(true));Turn=86;Fire(0);Admin.Run()
assert(H.qualificationErrors==0 and #H.profile.samples==1)
local p=NewPlanA(Env,NewProfile,WrapWindow,NewTrace,spy,142,0);assert(arity==5 and p.planFirstTurn==1)
''')

    def test_preanchor_resolves_only_after_actual_calendar_anchor(self):
        self.lua.execute('''Make(0);Turn=1;assert(Controller.RunNow(false)==false)
assert(H.preAnchor.pending==1 and H.preAnchor.validated==0 and H.profile.samples[1].preAnchor)
Clock=20;Fire(0);assert(H.preAnchor.pending==0 and H.preAnchor.validated==1)
assert(H.profile.samples[1].anchor==20 and not H.profile.samples[1].windowEligible and H.qualificationErrors==0)
''')
        self.setUp();self.lua.execute('''Make(210);Turn=211
Controller.RunNow(false,nil);assert(H.qualificationErrors==1 and #H.profile.samples==0 and H.preAnchor.pending==0)
''')

    def test_bad_pressure_calendar_rejected_before_event_subscription(self):
        self.lua.execute('''local adds=Adds
for _,t in ipairs({false,true,'0',{},-1,1.5,math.huge,-math.huge,0/0,2147483642})do
assert(not pcall(NewPlanA,Env,NewProfile,WrapWindow,NewTrace,NewDeferred,142,t))end
assert(not pcall(NewPlanA,Env,NewProfile,WrapWindow,NewTrace,NewDeferred,140,0))
assert(not pcall(NewPlanA,Env,NewProfile,WrapWindow,NewTrace,nil,142,0))
assert(Adds==adds)
''')

    def test_window_and_proof_bounds_reject_partial_and_malformed_values(self):
        self.lua.execute('''local p=NewProfile(function()return Clock end,4096)
local function wrap(a,b)return WrapWindow({profile=p,anchors={},planFirstTurn=a,planLastTurn=b},'Admin.Run',Body,{})end
assert(not pcall(wrap,nil,90));assert(not pcall(wrap,86,nil))
for _,pair in ipairs({{false,90},{86,false},{0,4},{1,6},{1.5,5.5},{math.huge,math.huge}})do
assert(not pcall(wrap,pair[1],pair[2]))
assert(not pcall(NewDeferred,p,{},function()end,pair[1],pair[2]))end
assert(not pcall(NewDeferred,p,{},function()end,nil,90))
assert(not pcall(NewDeferred,p,{},function()end,86,nil))
assert(type(wrap(1,5))=='function')
''')

    def test_original_arguments_returns_error_and_retirement(self):
        self.lua.execute('''local sentinel={}
Admin.Run=function(...)return select('#',...),...end
Controller.RunNow=function()error(sentinel,0)end
Make(210);Turn=211;Fire(0)
local n,a,b,c,d=Admin.Run(1,nil,false,nil);assert(n==4 and a==1 and b==nil and c==false and d==nil)
local ok,err=pcall(Controller.RunNow,false);assert(not ok and err==sentinel)
assert(H.profile.samples[2].failed)
local removed=H.Restore();assert(removed and H.retired and not H.enabled)
assert(not H.SetEnabled(true));local old=#H.profile.samples
Admin.Run();assert(#H.profile.samples==old)
''')


if __name__=='__main__':unittest.main()
