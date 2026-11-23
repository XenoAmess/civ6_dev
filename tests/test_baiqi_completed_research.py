"""Observed UI completed-current40/Core-1 boundary, using normal research API."""
from pathlib import Path
import sys,unittest
from lupa.lua51 import LuaRuntime as Lua51
from lupa.lua53 import LuaRuntime as Lua53
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT),str(ROOT/'tests')]
from tests.admin_cycle import run_admin_cycle

WORLD=r'''
local w=TestAdmin
w.turn=135;w.tech=40;w.coreTech=-1;w.civic=0;w.policyChanged=true
EndTurnBlockingTypes={ENDTURN_BLOCKING_RESEARCH=-286188551,NO_ENDTURN_BLOCKING=0}
NotificationManager={GetFirstEndTurnBlocking=function(pid)
 assert(pid==7)
 if w.blockerOverride~=nil then return w.blockerOverride end
 return w.coreTech==-1 and EndTurnBlockingTypes.ENDTURN_BLOCKING_RESEARCH or 0
end}
w.currentDone=true;w.progress={[40]=0,[41]=266,[42]=0,[43]=0,[46]=341}
w.cost={[40]=428,[41]=428,[42]=428,[43]=625,[46]=685}
w.legal={[41]=true,[42]=true,[43]=true,[46]=true};w.done={};w.logs={}
local rows={{Index=40,Hash=1040,TechnologyType='TECH_SANITATION',Repeatable=false},
 {Index=41,Hash=-2104580068,TechnologyType='TECH_ECONOMICS',Repeatable=false},
 {Index=42,Hash=-471009223,TechnologyType='TECH_RIFLING',Repeatable=false},
 {Index=43,Hash=1864094654,TechnologyType='TECH_FLIGHT',Repeatable=false},
 {Index=46,Hash=-1949163753,TechnologyType='TECH_ELECTRICITY',Repeatable=false}}
local by={};for _,r in ipairs(rows)do by[r.Index]=r;by[r.TechnologyType]=r end
GameInfo.Technologies=setmetatable(by,{__call=function()local i=0;return function()i=i+1;return rows[i]end end})
local t=Players[7]:GetTechs()
t.HasTech=function(_,i)if i==40 then return w.currentDone end;return w.done[i]==true end
t.CanResearch=function(_,i)if w.onCan then w.onCan(i)end;return w.legal[i]==true end
t.GetResearchProgress=function(_,i)return w.progress[i]end
t.GetResearchCost=function(_,i)return w.cost[i]end
t.GetResearchPath=function(_,hash)
 if w.pathShock then w.pathShock()end
 for _,r in ipairs(rows)do if r.Hash==hash then return{r.Index}end end
 error('UNEXPECTED_RESEARCH_HASH')
end
print=function(...)local r={};for n=1,select('#',...)do r[n]=tostring(select(n,...))end;w.logs[#w.logs+1]=table.concat(r,' ')end
'''

class CompletedCurrentResearch(unittest.TestCase):
    def fixture(self,vm,change=''):
        lua=vm(unpack_returned_tuples=True)
        lua.execute((ROOT/'tests/lua/mock_admin.lua').read_text(encoding='utf-8'));lua.execute(WORLD)
        for name in ['BaiqiConfig','BaiqiAdmin']:lua.execute((ROOT/f'mod/Baiqi/Lua/{name}.lua').read_text(encoding='utf-8'))
        if change:lua.execute(change)
        return lua,lua.globals().TestAdmin,lua.globals().BaiqiAdmin

    def test_observed_completed_ui_selection_continues_legal_normal_cost_research(self):
        for vm in [Lua51,Lua53]:
            with self.subTest(vm=vm.__module__):
                lua,w,a=self.fixture(vm);run_admin_cycle(a)
                self.assertEqual(len(w.requests),1)
                r=w.requests[1];self.assertEqual((r.pid,r.op,r.params.tech[1],r.params.mode),(7,1,41,3))
                self.assertEqual((w.progress[41],w.progress[46],w.tech,w.coreTech),(266,341,40,-1))

    def test_existing_active_unfinished_repeatable_and_unknown_current_are_preserved(self):
        changes=["TestAdmin.currentDone=false;TestAdmin.progress[40]=333.73046875", "GameInfo.Technologies[40].Repeatable=true;TestAdmin.legal[40]=true", "TestAdmin.currentDone=nil", "TestAdmin.currentDone='unknown'", "GameInfo.Technologies[40]=nil", "GameInfo.Technologies[40].Repeatable=nil", "GameInfo.Technologies[40].Hash=0", "TestAdmin.legal[40]=true"]
        for vm in [Lua51,Lua53]:
            for change in changes:
                with self.subTest(vm=vm.__module__,change=change):
                    lua,w,a=self.fixture(vm,change);run_admin_cycle(a);self.assertEqual(len(w.requests),0)

    def test_completed_ui_alone_cannot_override_active_or_unknown_backend_research(self):
        changes=['TestAdmin.coreTech=42','TestAdmin.blockerOverride=23669119','NotificationManager=nil','NotificationManager.GetFirstEndTurnBlocking=nil','EndTurnBlockingTypes.ENDTURN_BLOCKING_RESEARCH=nil']
        for vm in [Lua51,Lua53]:
            for change in changes:
                with self.subTest(vm=vm.__module__,change=change):
                    lua,w,a=self.fixture(vm,change);run_admin_cycle(a);self.assertEqual(len(w.requests),0)

    def test_pending_unknown_request_is_not_replayed_on_next_cycle_or_turn(self):
        for vm in [Lua51,Lua53]:
            with self.subTest(vm=vm.__module__):
                lua,w,a=self.fixture(vm);run_admin_cycle(a);self.assertEqual(len(w.requests),1)
                run_admin_cycle(a);w.turn=136;run_admin_cycle(a);self.assertEqual(len(w.requests),1)

    def test_native_state_drift_during_path_read_does_not_override_new_current_work(self):
        changes=['TestAdmin.currentDone=false','TestAdmin.tech=42','TestAdmin.turn=136','TestAdmin.legal[41]=false','GameInfo.Technologies[40].Repeatable=true','UI.IsGameCoreBusy=function()return true end','TestAdmin.coreTech=42','TestAdmin.blockerOverride=23669119']
        for vm in [Lua51,Lua53]:
            for change in changes:
                with self.subTest(vm=vm.__module__,change=change):
                    lua,w,a=self.fixture(vm,'TestAdmin.pathShock=function()'+change+' end');a.Run();self.assertEqual(len(w.requests),0)

    def test_normal_empty_selection_and_observed_application_keep_existing_investment(self):
        for vm in [Lua51,Lua53]:
            with self.subTest(vm=vm.__module__):
                lua,w,a=self.fixture(vm,'TestAdmin.tech=-1');run_admin_cycle(a);self.assertEqual(len(w.requests),1)
                w.tech,w.coreTech=41,41;run_admin_cycle(a);self.assertEqual(len(w.requests),1)
                self.assertEqual((w.progress[41],w.progress[46]),(266,341))

if __name__=='__main__':unittest.main()
