from pathlib import Path
import json,unittest
from lupa.lua51 import LuaRuntime
from tests import test_baiqi_settlement_border as border_fixture
ROOT=Path(__file__).resolve().parents[1]


class ExpansionStabilityPolicyTests(unittest.TestCase):
    def test_stability_unknown_shapes_ranking_and_input_preservation(self):
        data=json.loads((ROOT/'tests/fixtures/expansion_stability_cases.json').read_text(encoding='utf-8'))
        source=(ROOT/'mod/Baiqi/Lua/BaiqiPolicy.lua').read_text(encoding='utf-8')
        for name,code in data['cases'].items():
            with self.subTest(case=name):
                lua=LuaRuntime(unpack_returned_tuples=True);lua.execute(source)
                lua.execute(data['fixture']);lua.execute('M={Evaluate=BaiqiPolicy.ExpansionStability}');lua.execute(code)


class ExpansionStabilityControllerTests(unittest.TestCase):
    def setUp(self):
        fixture=border_fixture.SettlementBorderTests('runTest');fixture.setUp()
        self.lua,self.w,self.controller=fixture.lua,fixture.w,fixture.controller
        self.w.foreign=False;self.w.ownX,self.w.ownY=2,3
        self.lua.execute('''local w=TestWorld;w.ruleset='RULESET_EXPANSION_2';w.loyalty=100;w.loyaltyRate=20
TestWorld.objects.city.GetCulturalIdentity=function()
 if w.loyaltyError then error('loyalty unavailable')end
 return {GetLoyalty=function()return w.loyalty end,GetLoyaltyPerTurn=function()return w.loyaltyRate end}
end''')

    def run_now(self,count=2):
        for _ in range(count):self.controller.RunNow()
        self.assertNotIn('脚本错误',self.controller.GetStatus())

    def orders(self,op):return [r for r in self.w.unitRequests.values()if r.op==op]

    def test_stable_gs_owned_city_keeps_movement(self):
        self.run_now();self.assertEqual(len(self.orders(10)),1)

    def test_rise_fall_uses_same_real_loyalty_gate(self):
        self.w.ruleset='RULESET_EXPANSION_1';self.w.loyaltyRate=-1;self.run_now()
        self.assertEqual(self.orders(10),[])

    def test_negative_pressure_stops_new_expansion(self):
        self.w.loyaltyRate=-1;self.run_now();self.assertEqual(self.orders(10),[])

    def test_governor_rescued_low_loyalty_still_waits(self):
        self.w.loyalty,self.w.loyaltyRate=13.28125,1.796875
        self.run_now();self.assertEqual(self.orders(10),[])

    def test_recovery_to_fifty_resumes_without_switch(self):
        self.w.loyalty=49;self.run_now();self.assertEqual(self.orders(10),[])
        self.w.loyalty,self.w.turn=50,2;self.run_now()
        self.assertEqual(len(self.orders(10)),1)

    def test_base_does_not_read_unsupported_loyalty_methods(self):
        self.w.ruleset='RULESET_STANDARD';self.w.loyaltyError=True
        self.run_now();self.assertEqual(len(self.orders(10)),1)

    def test_unknown_ruleset_or_getter_waits_without_controller_error(self):
        for code in ("TestWorld.ruleset='RULESET_UNKNOWN'",'TestWorld.loyaltyError=true',
                     "GameConfiguration.GetValue=function()return nil end"):
            with self.subTest(code=code):
                self.setUp();self.lua.execute(code);self.run_now()
                self.assertEqual(self.orders(10),[])

    def test_empty_empire_first_city_preserved(self):
        self.w.withCity=False;self.w.loyaltyError=True
        self.run_now(1);self.assertEqual(len(self.orders(11)),1)

    def test_stability_lost_during_move_qualification_stops_write(self):
        self.lua.execute('''local old=UnitManager.CanStartOperation
UnitManager.CanStartOperation=function(u,op,...)
 local can=old(u,op,...);if op==10 then TestWorld.loyaltyRate=-1 end;return can
end''')
        self.run_now();self.assertEqual(self.orders(10),[])

    def select_then_arrive(self):
        self.run_now(1);self.assertEqual(len(self.orders(10)),1)
        self.w.turn,self.w.settlerPlot=2,47

    def test_existing_goal_cannot_found_after_owned_city_declines(self):
        self.select_then_arrive()
        self.lua.execute('''local b=ExposedMembers.BaiqiSettlerGoalsBridge;local original=b.Forget
TestWorld.goalForgets=0;b.Forget=function(...)TestWorld.goalForgets=TestWorld.goalForgets+1;return original(...)end''')
        self.w.loyalty=49;self.run_now()
        self.assertEqual(self.orders(11),[])
        self.assertEqual(self.w.goalForgets,0)
        self.w.loyalty,self.w.turn=50,3;self.run_now()
        self.assertEqual(len(self.orders(11)),1)

    def test_stability_lost_during_found_qualification_stops_write(self):
        self.select_then_arrive()
        self.lua.execute('''local old=UnitManager.CanStartOperation;local n=0
UnitManager.CanStartOperation=function(u,op,...)
 local can=old(u,op,...);if op==11 then n=n+1;if n==2 then TestWorld.loyaltyRate=-1 end end;return can
end''')
        self.run_now();self.assertEqual(self.orders(11),[])

    def test_domestic_production_continues_while_expansion_holds(self):
        self.w.loyalty=10;self.w.queueSize=0;self.w.withSettler=False
        self.run_now(1)
        self.assertGreater(len(self.w.cityRequests),0)
        self.assertEqual(self.orders(10),[])

    def recruitment_world(self):
        self.w.queueSize=0;self.w.withSettler=False
        self.lua.execute('''local o=TestWorld.objects
o.city.GetPopulation=function()return 5 end
o.player.GetTreasury=function()return {GetGoldBalance=function()return 10000 end,
 GetGoldYield=function()return 1000 end,GetTotalMaintenance=function()return 0 end}end''')

    def test_new_settler_training_waits_for_city_recovery(self):
        for loyalty,rate,expected in ((100,20,True),(49,20,False),(100,-1,False),(50,0,True)):
            with self.subTest(loyalty=loyalty,rate=rate):
                self.setUp();self.recruitment_world();self.w.loyalty,self.w.loyaltyRate=loyalty,rate
                self.run_now(1)
                self.assertGreater(len(self.w.cityRequests),0)
                key=self.lua.globals().CityOperationTypes.PARAM_UNIT_TYPE
                self.assertEqual(any(r[key]==201 for r in self.w.cityRequests.values()),expected)

    def test_new_settler_training_rechecks_after_native_cost_qualification(self):
        self.recruitment_world()
        self.lua.execute('''local q=TestWorld.objects.city:GetBuildQueue();local original=q.CanProduce
q.CanProduce=function(self,hash,...)
 local allowed=original(self,hash,...)
 if hash==201 then TestWorld.loyaltyRate=-1 end
 return allowed
end''')
        self.run_now(1)
        key=self.lua.globals().CityOperationTypes.PARAM_UNIT_TYPE
        self.assertFalse(any(r[key]==201 for r in self.w.cityRequests.values()))
