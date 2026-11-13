from pathlib import Path
import unittest
from lupa.lua51 import LuaRuntime

ROOT=Path(__file__).resolve().parents[1]


class DiagnosticPlanStageTests(unittest.TestCase):
    def setUp(self):
        self.lua=LuaRuntime(unpack_returned_tuples=True)
        for stem,name in [('diagnostic_profile','NewProfile'),
                          ('diagnostic_plan_window','WrapWindow'),
                          ('diagnostic_plan_stage','NewPlanA')]:
            self.lua.globals()[name]=self.lua.execute(
                (ROOT/f'tools/lua/{stem}.lua').read_text(encoding='utf-8'))
        self.lua.execute('''Turn=85;Clock=10;LP=0;Calls=0;Adds=0;Removes=0;Handlers={}
Event={Add=function(fn) Adds=Adds+1;Handlers[#Handlers+1]=fn;if AddError then error('add') end end,
 Remove=function(fn) Removes=Removes+1;if RemoveError then error('remove') end
  for i,f in ipairs(Handlers) do if f==fn then table.remove(Handlers,i);return end end end}
Env={Game={GetLocalPlayer=function() if GetterError then error('qa') end;return LP end,
 GetCurrentGameTurn=function() return Turn end},Automation={GetTime=function() return Clock end},
 Players={[0]={IsTurnActive=function() return true end,
 GetCities=function() return {GetCount=function() return 10 end} end}},
 Events={PlayerTurnActivated=Event}}
function Body(...) Calls=Calls+1;Clock=Clock+0.01;return ... end
Admin={Run=Body};Controller={RunNow=Body}
function Fire(pid) for _,f in ipairs(Handlers) do f(pid) end end
H=NewPlanA(Env,NewProfile,WrapWindow)''')

    def test_first_anchor_precedes_gameplay_and_duplicate_keeps_first_time(self):
        self.lua.execute('''assert(Adds==1 and H.profile.capacity==4096 and not H.profile.aggregateZero)
assert(H.Bind(Admin,Controller));assert(not H.Bind(Admin,Controller));assert(H.SetEnabled(true))
Event.Add(function() if Turn==86 then assert(Admin.Run(7,nil,false)==7) end end)
Turn=86;Fire(0);Clock=15;Fire(0)
assert(H.anchors[86]==10 and H.anchorCount==1 and #H.profile.samples==2)
assert(H.profile.samples[1].windowEligible and H.profile.samples[2].cityEnd==10)''')

    def test_ports_are_real_and_all_parameters_preserved(self):
        self.lua.execute('''assert(H.Bind(Admin,Controller) and H.SetEnabled(true))
Turn=86;Fire(0);local function Save(...) return select('#',...),... end
local n,a,b,c,d=Save(Controller.RunNow(3,nil,false,nil))
assert(n==4 and a==3 and b==nil and c==false and d==nil)
assert(H.profile.samples[1].name=='Controller.RunNow' and H.qualificationErrors==0)''')

    def test_qa_callback_failure_does_not_prevent_later_subscriber(self):
        self.lua.execute('''assert(H.Bind(Admin,Controller) and H.SetEnabled(true))
Event.Add(function() Calls=Calls+1 end);GetterError=true;Fire(0)
assert(Calls==1 and H.qualificationErrors==1 and H.anchorCount==0)
GetterError=false;LP=1;Fire(1);assert(H.qualificationErrors==1)
LP=0;Turn=0/0;Fire(0);assert(H.qualificationErrors==2 and Calls==3)''')

    def test_restore_preserves_foreign_bindings_and_other_callbacks(self):
        self.lua.execute('''assert(H.Bind(Admin,Controller) and H.SetEnabled(true))
local foreign=function() return 12 end;Admin.Run=foreign
Event.Add(function() Calls=Calls+1 end)
local ok,same=H.Restore();assert(ok and not same[1] and same[2])
assert(Admin.Run==foreign and Controller.RunNow==Body and Removes==1 and #Handlers==1)
assert(not H.SetEnabled(true) and not H.Bind(Admin,Controller))
H.Restore();Fire(0);assert(Removes==1 and Calls==1 and H.retired and not H.enabled)''')

    def test_add_remove_unknown_never_claims_success_or_retries_unknown_remove(self):
        self.lua.execute('''AddError=true;local bad=NewPlanA(Env,NewProfile,WrapWindow)
assert(bad.qualificationErrors==1 and bad.subscribed==nil and not bad.Bind(Admin,Controller))
RemoveError=true;local ok=bad.Restore();assert(not ok and bad.qualificationErrors==2)
local old=Removes;ok=bad.Restore();assert(not ok and Removes==old)
assert(not bad.SetEnabled(true))''')

    def test_bad_bind_is_prevalidated_and_outside_turns_create_no_anchors(self):
        self.lua.execute('''local before=Admin.Run
assert(not H.Bind(Admin,{}) and Admin.Run==before and not H.bound)
assert(H.Bind(Admin,Controller) and not H.SetEnabled(true))
local clean=NewPlanA(Env,NewProfile,WrapWindow)
assert(clean.Bind({Run=Body},{RunNow=Body}) and clean.SetEnabled(true))
Turn=84;Fire(0);Turn=92;Fire(0);assert(clean.anchorCount==0)
Turn=91;Fire(0);assert(clean.anchorCount==1 and clean.anchors[91]==10)''')


if __name__=='__main__':
    unittest.main()
