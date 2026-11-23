"""Minimal consumer of actual137 unassigned Governors+4; both Lua VMs."""
from pathlib import Path
import sys,unittest
from lupa.lua51 import LuaRuntime as Lua51
from lupa.lua53 import LuaRuntime as Lua53
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT),str(ROOT/'tests')]
from tests.admin_cycle import run_admin_cycle

WORLD=r'''
local w=TestAdmin;local g=w.gov;local pg=Players[7]:GetGovernors()
w.policyChanged=true;g.base={[1]=21,[2]=-0.34375,[3]=18,[4]=21}
g.loyalty={[1]=100,[2]=100,[3]=100,[4]=100};g.passive={[3]=4,[4]=4}
g.cities[3]={GetID=function()return 3 end,GetOwner=function()return 7 end,GetPopulation=function()return 8 end}
g.cities[4]={GetID=function()return 4 end,GetOwner=function()return 7 end,GetPopulation=function()return 6 end}
for i,c in ipairs(g.cities)do local id=i
 c.GetCulturalIdentity=function()
  local function contribution()return(pg:GetAssignedGovernor(c)and(id==1 and 12 or 8)or 0)+(g.passive[id]or 0)end
  return {GetLoyalty=function()return g.loyalty[id]end,
   GetLoyaltyPerTurn=function()return g.base[id]+contribution()end,
   GetIdentitySourcesBreakdown=function()
    if g.breakdownError then error('unknown actual category')end
    if g.badShape then return {extra={Governors=4}}end
    if g.mismatch and id==3 then return {{PopulationPressure=18},{Governors=3}}end
    if g.nonNumeric and id==3 then return {{PopulationPressure=18},{Governors='4'}}end
    return {{PopulationPressure=g.base[id]},{Governors=contribution()}}
   end}
 end
end
'''


class PassiveGovernorContribution(unittest.TestCase):
    def fixture(self,vm,change=''):
        lua=vm(unpack_returned_tuples=True)
        for name in ['tests/lua/mock_admin.lua','tests/lua/mock_governors.lua','tests/lua/mock_governor_loyalty.lua','mod/Baiqi/Lua/BaiqiConfig.lua','mod/Baiqi/Lua/BaiqiGovernorLoyalty.lua']:
            lua.execute((ROOT/name).read_text(encoding='utf-8'))
        lua.execute(WORLD);lua.execute((ROOT/'mod/Baiqi/Lua/BaiqiAdmin.lua').read_text(encoding='utf-8'))
        if change:lua.execute(change)
        return lua,lua.globals().TestAdmin,lua.globals().TestAdmin.gov,lua.globals().BaiqiAdmin

    def cycle(self,a):
        run_admin_cycle(a);run_admin_cycle(a)

    def test_actual_passive_categories_elsewhere_allow_one_normal_rescue_and_observed_application(self):
        for vm in [Lua51,Lua53]:
            with self.subTest(vm=vm.__module__):
                lua,w,g,a=self.fixture(vm);self.cycle(a)
                self.assertEqual(len(g.requests),1)
                r=g.requests[1];self.assertEqual((r.pid,r.op,r.params.governor,r.params.owner,r.params.city),(7,11,3,7,2))
                self.assertEqual((g.points,g.spent,g.owned[930].city.GetID()),(6,6,1))
                g.Apply();self.cycle(a)
                self.assertEqual((len(g.requests),g.spent,g.owned[930].city.GetID()),(1,6,2))
                self.assertEqual(g.cities[2].GetCulturalIdentity().GetLoyaltyPerTurn(),7.65625)
                self.assertEqual((g.cities[1].GetCulturalIdentity().GetLoyaltyPerTurn(),g.cities[3].GetCulturalIdentity().GetLoyaltyPerTurn()),(21,22))

    def test_passive_category_in_unassigned_crisis_is_not_own_governor_removal(self):
        for vm in [Lua51,Lua53]:
            with self.subTest(vm=vm.__module__):
                lua,w,g,a=self.fixture(vm,'TestAdmin.gov.passive[2]=4;TestAdmin.gov.base[2]=-4.34375');self.cycle(a)
                self.assertEqual(len(g.requests),1)
                self.assertEqual(g.requests[1].params.city,2)
                self.assertIsNone(lua.globals().Players[7].GetGovernors().GetAssignedGovernor(g.cities[2]))

    def test_no_actual_crisis_does_not_reassign_from_passive_positive_values(self):
        for vm in [Lua51,Lua53]:
            with self.subTest(vm=vm.__module__):
                lua,w,g,a=self.fixture(vm,'TestAdmin.gov.base[2]=1');self.cycle(a)
                self.assertEqual(len(g.requests),0)

    def test_unknown_negative_malformed_or_unsafe_donor_still_holds(self):
        changes=['TestAdmin.gov.passive[3]=-4','TestAdmin.gov.passive[3]=0/0','TestAdmin.gov.mismatch=true','TestAdmin.gov.nonNumeric=true','TestAdmin.gov.badShape=true','TestAdmin.gov.breakdownError=true','TestAdmin.gov.base[1]=0','TestAdmin.gov.neutralized=1','TestAdmin.gov.illegal[2]=true']
        for vm in [Lua51,Lua53]:
            for change in changes:
                with self.subTest(vm=vm.__module__,change=change):
                    lua,w,g,a=self.fixture(vm,change);self.cycle(a);self.assertEqual(len(g.requests),0)

    def test_unknown_false_throwing_request_does_not_replay_next_cycle_or_turn(self):
        for vm in [Lua51,Lua53]:
            for change in ['', 'TestAdmin.gov.requestFalse=true', 'TestAdmin.gov.requestError=true']:
                with self.subTest(vm=vm.__module__,change=change):
                    lua,w,g,a=self.fixture(vm,change);self.cycle(a);self.assertEqual(len(g.requests),1)
                    w.turn=2;self.cycle(a);self.assertEqual(len(g.requests),1)
                    self.assertEqual(g.owned[930].city.GetID(),1)

    def test_state_drift_after_final_native_permission_holds_without_request(self):
        for vm in [Lua51,Lua53]:
            with self.subTest(vm=vm.__module__):
                lua,w,g,a=self.fixture(vm,'TestAdmin.gov.onPermission=function(n)if n==3 then TestAdmin.gov.base[2]=-20 end end');self.cycle(a)
                self.assertGreaterEqual(g.permissionReads,3)
                self.assertEqual(len(g.requests),0)


if __name__=='__main__':unittest.main()
