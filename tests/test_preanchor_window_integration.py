from pathlib import Path
import unittest
from lupa.lua51 import LuaRuntime

ROOT=Path(__file__).resolve().parents[1]


class PreanchorWindowIntegrationTests(unittest.TestCase):
    def setUp(self):
        self.lua=LuaRuntime(unpack_returned_tuples=True)
        for stem,name in [('diagnostic_profile','NewProfile'),('diagnostic_plan_window','WrapWindow'),
                          ('diagnostic_qualification_trace','NewTrace'),
                          ('diagnostic_preanchor_proof','NewDeferred'),('diagnostic_plan_stage','NewPlanA')]:
            self.lua.globals()[name]=self.lua.execute((ROOT/f'tools/lua/{stem}.lua').read_text(encoding='utf-8'))
        self.lua.execute('''rawget=nil;rawset=nil;Turn=86;Clock=1;Calls=0;Handlers={}
Env={Game={GetCurrentGameTurn=function()return Turn end,GetLocalPlayer=function()return 0 end},
 Automation={GetTime=function()return Clock end},Players={[0]={IsTurnActive=function()return true end,
 GetCities=function()return {GetCount=function()return 10 end}end}},
 Events={PlayerTurnActivated={Add=function(f)Handlers[#Handlers+1]=f end,Remove=function()end}}}
function Body(...)Calls=Calls+1;Clock=Clock+1;return ...end
Admin={Run=Body};Controller={RunNow=Body}
H=NewPlanA(Env,NewProfile,WrapWindow,NewTrace,NewDeferred)
assert(H.source=='baiqi140-stageA-v2'and H.Bind(Admin,Controller)and H.SetEnabled(true))
function Native()for _,f in ipairs(Handlers)do f(0,false)end end''')

    def test_false_call_retained_pending_then_proved_before_real_native_event(self):
        self.lua.execute('''assert(Controller.RunNow(false)==false and Calls==1)
assert(H.qualificationErrors==0 and H.preAnchor.pending==1 and H.profile.totalCalls==1)
local row=H.profile.samples[1]
assert(row.preAnchor and row.argumentCount==1 and row.allowOrders=='false'and row.anchor==nil)
Clock=10;Native();assert(H.preAnchor.pending==0 and H.preAnchor.validated==1 and row.anchor==10)
Controller.RunNow(true);assert(#H.profile.samples==2 and not H.profile.samples[2].preAnchor)
assert(H.profile.samples[2].allowOrders=='true'and H.qualificationErrors==0)''')

    def test_missing_anchor_for_true_nil_or_admin_is_still_unknown(self):
        self.lua.execute('''Controller.RunNow(true);Controller.RunNow();Admin.Run(false)
assert(Calls==3 and H.profile.totalCalls==0 and H.qualificationErrors==3)
assert(H.preAnchor.recorded==0 and H.preAnchor.pending==0)''')

    def test_reentrant_event_overlap_is_unknown_and_does_not_block_body(self):
        self.lua.execute('''H.Restore();Clock=1
local original=function(value)Clock=2;Native();Clock=3;return value end
Admin={Run=Body};Controller={RunNow=original}
H=NewPlanA(Env,NewProfile,WrapWindow,NewTrace,NewDeferred)
assert(H.Bind(Admin,Controller)and H.SetEnabled(true))
assert(Controller.RunNow(false)==false)
assert(H.preAnchor.pending==0 and H.preAnchor.errors==1 and H.preAnchor.validated==0)
assert(H.qualificationErrors==1 and H.profile.samples[1].ended==3)''')

    def test_original_error_survives_pending_proof_and_capacity_is_not_bypassed(self):
        self.lua.execute('''local sentinel={}
local f=WrapWindow(H,'Controller.RunNow',function(value)Clock=Clock+1;error(sentinel,0)end,
 {Turn=function()return Turn end,LocalPlayer=function()return 0 end,Active=function()return true end,
 Now=function()return Clock end,CityCount=function()return 10 end})
local ok,err=pcall(f,false);assert(not ok and err==sentinel and H.preAnchor.pending==1)
Clock=10;Native();assert(H.preAnchor.errors==1 and H.preAnchor.validated==0)
assert(H.profile.capacity==4096 and #H.profile.samples==1 and H.profile.samples[1].failed)''')


if __name__=='__main__':
    unittest.main()
