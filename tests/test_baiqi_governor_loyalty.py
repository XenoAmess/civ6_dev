from pathlib import Path
import json,unittest
from lupa.lua51 import LuaRuntime
ROOT=Path(__file__).resolve().parents[1]


class GovernorLoyaltyPlannerTests(unittest.TestCase):
    def test_crisis_ranking_safety_unknown_shapes_and_no_input_mutation(self):
        data=json.loads((ROOT/'tests/fixtures/governor_loyalty_cases.json').read_text(encoding='utf-8'))
        source=(ROOT/'mod/Baiqi/Lua/BaiqiGovernorLoyalty.lua').read_text(encoding='utf-8')
        for name,code in data['cases'].items():
            with self.subTest(case=name):
                lua=LuaRuntime(unpack_returned_tuples=True)
                lua.execute(data['fixture']);lua.globals().M=lua.execute(source);lua.execute(code)


class GovernorLoyaltyConsumerTests(unittest.TestCase):
    def setUp(self):
        self.lua=LuaRuntime(unpack_returned_tuples=True)
        for name in ('tests/lua/mock_admin.lua','tests/lua/mock_governors.lua',
                     'tests/lua/mock_governor_loyalty.lua','mod/Baiqi/Lua/BaiqiConfig.lua',
                     'mod/Baiqi/Lua/BaiqiGovernorLoyalty.lua','mod/Baiqi/Lua/BaiqiAdmin.lua'):
            self.lua.execute((ROOT/name).read_text(encoding='utf-8'))
        self.w=self.lua.globals().TestAdmin
        self.g=self.w.gov
        self.admin=self.lua.globals().BaiqiAdmin
        self.w.policyChanged=True

    def run_admin(self,count=2):
        for _ in range(count):self.admin.Run()

    def test_crisis_outranks_population_and_waits_for_real_assignment(self):
        self.run_admin()
        self.assertEqual(len(self.g.requests),1)
        self.assertEqual((self.g.requests[1].op,self.g.requests[1].params.city), (11,2))
        self.assertEqual(self.g.owned[930].city.GetID(),1)
        self.g.Apply();self.run_admin()
        self.assertEqual(self.g.owned[930].city.GetID(),2)
        self.assertEqual((self.g.spent,len(self.g.requests)),(6,1))
        self.assertAlmostEqual(self.g.cities[2].GetCulturalIdentity().GetLoyaltyPerTurn(),1.71875)

    def test_pending_does_not_replay_next_turn(self):
        self.run_admin();self.w.turn=2;self.run_admin()
        self.assertEqual((len(self.g.requests),self.g.owned[930].city.GetID()),(1,1))

    def test_false_ack_does_not_cancel_or_replay(self):
        self.g.requestFalse=True;self.run_admin();self.w.turn=2;self.run_admin()
        self.assertEqual(len(self.g.requests),1)

    def test_throwing_native_does_not_stop_other_admin_or_replay(self):
        self.g.requestError=True;self.run_admin();self.w.turn=2;self.run_admin()
        self.assertEqual(len(self.g.requests),1)
        self.assertGreaterEqual(len(self.w.requests),2)

    def test_no_crisis_preserves_existing_governor(self):
        self.g.base[2]=1;self.run_admin()
        self.assertEqual(len(self.g.requests),0)

    def test_neutralized_governor_stays(self):
        self.g.neutralized=2;self.run_admin();self.assertEqual(len(self.g.requests),0)

    def test_unsafe_donor_stays(self):
        self.g.base[1]=0;self.run_admin();self.assertEqual(len(self.g.requests),0)

    def test_extra_governor_effects_are_removed_in_full(self):
        self.g.removal=12;self.g.base[1]=-1;self.run_admin()
        self.assertEqual(len(self.g.requests),0)

    def test_unknown_pressure_or_breakdown_does_not_stop_research(self):
        for field in ('pressureError','breakdownError'):
            with self.subTest(field=field):
                self.setUp();setattr(self.g,field,True);self.run_admin()
                self.assertEqual(len(self.g.requests),0)
                self.assertGreaterEqual(len(self.w.requests),2)

    def test_native_denied_target_waits(self):
        self.g.illegal[2]=True;self.run_admin();self.assertEqual(len(self.g.requests),0)

    def changed_during_final_permission(self,code):
        self.lua.execute('TestAdmin.gov.onPermission=function(n)if n==3 then '+code+' end end')
        self.run_admin(1);self.assertEqual(len(self.g.requests),0)

    def test_donor_loses_safety_after_permission(self):
        self.changed_during_final_permission('TestAdmin.gov.base[1]=-1')

    def test_target_pressure_worsens_after_permission(self):
        self.changed_during_final_permission('TestAdmin.gov.base[2]=-20')

    def test_target_becomes_foreign_after_permission(self):
        self.changed_during_final_permission('TestAdmin.gov.foreign=true')

    def test_target_nan_after_permission_waits(self):
        self.changed_during_final_permission('TestAdmin.gov.base[2]=0/0')

    def test_turn_or_leader_changes_after_permission(self):
        for code in ('TestAdmin.turn=2',"TestAdmin.leader='LEADER_TRAJAN'"):
            with self.subTest(code=code):
                self.setUp();self.changed_during_final_permission(code)

    def test_base_game_missing_governors_preserves_research(self):
        self.lua.execute('Players[7].GetGovernors=nil;GameInfo.Governors=nil')
        self.run_admin();self.assertGreaterEqual(len(self.w.requests),2)
