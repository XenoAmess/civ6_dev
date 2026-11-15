from tests.admin_cycle import run_admin_cycle
"""Salvageable coastal damage can justify research switching without losing investment."""
import unittest
from lupa.lua51 import LuaRuntime as Lua51
from lupa.lua53 import LuaRuntime as Lua53
import test_baiqi_flood as flood


class FloodResearchInterruptTests(unittest.TestCase):
    def fixture(self, runtime):
        previous = flood.LuaRuntime
        flood.LuaRuntime = runtime
        try:
            case = flood.FloodResearchTests(methodName='runTest')
            case.setUp()
        finally:
            flood.LuaRuntime = previous
        case.lua.execute('''
local w=TestAdmin
w.oldProgress=333.73046875;w.oldCost=925;w.oldOwned=false
w.targetProgress=413;w.targetCost=664;w.logs={}
print=function(...)local t={};for i=1,select('#',...)do t[i]=tostring(select(i,...))end;w.logs[#w.logs+1]=table.concat(t,' ')end
local t=Players[7]:GetTechs();local has,path=t.HasTech,t.GetResearchPath
t.HasTech=function(self,index)if index==0 then return w.oldOwned end;return has(self,index)end
t.GetResearchProgress=function(_,index)
 if w.progressReadShock then w.progressReadShock(index)end
 if index==0 then if w.throwOldProgress then error('old progress unknown')end;return w.oldProgress end
 if index==55 then return w.targetProgress end
 error('unexpected research index')
end
t.GetResearchCost=function(_,index)
 if index==0 then return w.oldCost end
 if index==55 then return w.targetCost end
 return 25
end
t.GetResearchPath=function(self,hash)
 local result=path(self,hash)
 if hash==555 then if w.badPath then return w.badPath end;return {55}end
 return result
end
''')
        return case

    @staticmethod
    def logs(case):
        return '\n'.join(case.w.logs.values())

    def test_urgent_flood_switches_to_direct_index_path_and_preserves_old_investment(self):
        for runtime in (Lua51, Lua53):
            case = self.fixture(runtime)
            run_admin_cycle(case.a); run_admin_cycle(case.a)
            self.assertEqual(len(case.w.requests), 1)
            request = case.w.requests[1]
            self.assertEqual((request.pid, request.op, request.params.tech[1], request.params.mode), (7, 1, 55, 3))
            self.assertEqual((case.w.oldProgress, case.w.oldCost), (333.73046875, 925))

    def test_nonflood_unknown_submerged_owned_and_unresearchable_target_keep_current_work(self):
        for runtime in (Lua51, Lua53):
            for change in ('TestFlood.flooded=false', 'TestFlood.flooded=nil',
                           'TestFlood.submerged=true', 'TestFlood.owner=8',
                           'TestAdmin.owned=true', 'TestAdmin.can=false', 'TestAdmin.can=nil',
                           'TestAdmin.tech=55'):
                case = self.fixture(runtime)
                case.lua.execute(change); run_admin_cycle(case.a)
                self.assertEqual(len(case.w.requests), 0)

    def test_invalid_or_unknown_old_investment_never_authorizes_switch(self):
        for runtime in (Lua51, Lua53):
            for change in ('w.oldProgress=nil', 'w.oldProgress=-1', 'w.oldProgress=0/0',
                           'w.oldProgress=math.huge', 'w.oldProgress=w.oldCost',
                           'w.oldCost=nil', 'w.oldCost=0', 'w.oldCost=0/0',
                           'w.oldCost=math.huge', 'w.oldOwned=true', 'w.oldOwned=nil',
                           'w.throwOldProgress=true', 'GameInfo.Technologies[0].Hash=0',
                           'GameInfo.Technologies[0].TechnologyType=nil'):
                with self.subTest(lua=runtime, change=change):
                    case = self.fixture(runtime)
                    case.lua.execute('local w=TestAdmin;'+change); run_admin_cycle(case.a)
                    self.assertEqual(len(case.w.requests), 0)

    def test_path_read_cannot_cover_old_target_demand_or_scope_drift(self):
        for runtime in (Lua51, Lua53):
            for change in ('w.oldProgress=w.oldProgress+1', 'w.oldCost=w.oldCost+1',
                           'w.oldOwned=true', 'w.tech=1', 'w.turn=2', 'w.can=false',
                           'w.owned=true', 'w.leader="OTHER"', 'TestFlood.flooded=false',
                           'TestFlood.submerged=true', 'GameInfo.Technologies[0].Hash=101',
                           'GameInfo.Technologies[0].TechnologyType="OTHER"',
                           'UI.IsGameCoreBusy=function()return true end'):
                with self.subTest(lua=runtime, change=change):
                    case = self.fixture(runtime)
                    case.lua.execute('TestAdmin.pathShock=function()local w=TestAdmin;'+change+' end')
                    # Observe the drifting research callback itself. Later
                    # callbacks can legitimately qualify a new current turn.
                    case.a.Run(); self.assertEqual(len(case.w.requests), 0)

    def test_future_hash_sparse_or_ambiguous_paths_are_rejected(self):
        for runtime in (Lua51, Lua53):
            for path in ('{555}', '{55,56}', '{[2]=55}', '{[0]=55}', '{["1"]=55}',
                         'setmetatable({55},{})'):
                case = self.fixture(runtime)
                case.lua.execute('TestAdmin.badPath='+path); run_admin_cycle(case.a)
                self.assertEqual(len(case.w.requests), 0)

    def test_initial_unknown_progress_cannot_be_coerced_to_zero(self):
        for runtime in (Lua51, Lua53):
            for first in ('nil', 'false'):
                case = self.fixture(runtime)
                case.lua.execute('''local t=Players[7]:GetTechs();local previous=t.GetResearchProgress;local n=0
t.GetResearchProgress=function(self,index)
 if index==0 then n=n+1;if n==1 then return '''+first+''' end;return 0 end
 return previous(self,index)
end''')
                run_admin_cycle(case.a); self.assertEqual(len(case.w.requests), 0)

    def test_target_hash_drift_does_not_requalify_the_mutated_row(self):
        for runtime in (Lua51, Lua53):
            case = self.fixture(runtime)
            case.lua.execute('TestAdmin.pathShock=function()GameInfo.Technologies[55].Hash=556 end')
            run_admin_cycle(case.a); self.assertEqual(len(case.w.requests), 0)

    def test_unknown_or_throwing_writer_is_never_replayed(self):
        for runtime in (Lua51, Lua53):
            for throws in (False, True):
                case = self.fixture(runtime)
                case.w.throwWriter = throws; run_admin_cycle(case.a); case.w.throwWriter = False
                case.w.turn = 2; run_admin_cycle(case.a); run_admin_cycle(case.a)
                self.assertEqual(len(case.w.requests), 1)
                self.assertNotIn('research_observed', self.logs(case))

    def test_target_observed_without_old_investment_preservation_stays_pending(self):
        for runtime in (Lua51, Lua53):
            for change in ('w.oldProgress=w.oldProgress-1', 'w.oldProgress=nil',
                           'w.oldProgress=0/0', 'w.oldCost=nil', 'w.oldOwned=nil',
                           'w.throwOldProgress=true', 'GameInfo.Technologies[0].Hash=101'):
                case = self.fixture(runtime)
                run_admin_cycle(case.a); self.assertEqual(len(case.w.requests), 1)
                case.w.tech = 55
                case.lua.execute('local w=TestAdmin;'+change); run_admin_cycle(case.a)
                self.assertNotIn('research_observed', self.logs(case))
                case.w.tech = -1; case.w.owned = True; case.w.turn = 2
                run_admin_cycle(case.a); run_admin_cycle(case.a)
                self.assertEqual(len(case.w.requests), 1)

    def test_retained_or_legitimately_completed_old_work_allows_observed_ack(self):
        for runtime in (Lua51, Lua53):
            for change in ('', 'TestAdmin.oldProgress=334', 'TestAdmin.oldOwned=true'):
                case = self.fixture(runtime)
                run_admin_cycle(case.a); self.assertEqual(len(case.w.requests), 1)
                case.w.tech = 55; case.lua.execute(change); run_admin_cycle(case.a)
                self.assertIn('research_observed', self.logs(case))
                case.w.tech = -1; case.w.owned = True; case.w.turn = 2; run_admin_cycle(case.a)
                self.assertEqual(len(case.w.requests), 2)


if __name__ == '__main__':
    unittest.main()
