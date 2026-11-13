"""Demand reads skip unused breakdowns while real rescue keeps fresh safety checks."""
from pathlib import Path
import unittest

from tests import test_baiqi_governor_loyalty as existing

ROOT = Path(__file__).resolve().parents[1]


class GovernorDemandReadTests(unittest.TestCase):
    def setUp(self):
        self.f = existing.GovernorLoyaltyConsumerTests(methodName='runTest')
        self.f.setUp()
        self.lua, self.g = self.f.lua, self.f.g
        self.lua.execute('''
          local g=TestAdmin.gov;g.breakdownReads=0;g.rateReads=0
          for _,city in ipairs(g.cities)do
            local get=city.GetCulturalIdentity
            city.GetCulturalIdentity=function(...)
              local ci=get(...);local breakdown,rate=ci.GetIdentitySourcesBreakdown,ci.GetLoyaltyPerTurn
              ci.GetIdentitySourcesBreakdown=function(...)g.breakdownReads=g.breakdownReads+1;return breakdown(...)end
              ci.GetLoyaltyPerTurn=function(...)g.rateReads=g.rateReads+1;return rate(...)end
              return ci
            end
          end
        ''')

    def test_positive_demand_skips_all_breakdowns_and_keeps_other_admin(self):
        self.g.base[2] = 1
        self.f.run_admin()
        self.assertEqual((self.g.breakdownReads, len(self.g.requests)), (0, 0))
        self.assertGreater(self.g.rateReads, 0)
        self.assertGreaterEqual(len(self.f.w.requests), 2)

    def test_assigned_negative_city_is_not_a_rescue_target(self):
        self.g.base[1], self.g.base[2] = -10, 1
        self.f.run_admin()
        self.assertEqual((self.g.breakdownReads, len(self.g.requests)), (0, 0))

    def test_later_callback_rechecks_demand_without_cache(self):
        self.g.base[2] = 1
        self.f.run_admin(1)
        self.assertEqual(self.g.breakdownReads, 0)
        self.g.base[2] = -0.001
        self.f.run_admin(1)
        self.assertEqual(len(self.g.requests), 1)
        self.assertGreaterEqual(self.g.breakdownReads, 4)
        self.assertEqual(self.g.requests[1].params.city, 2)

    def test_negative_probe_is_not_permission_when_full_read_changes(self):
        self.lua.execute('''
          local c=TestAdmin.gov.cities[2];local get=c.GetCulturalIdentity;local n=0
          c.GetCulturalIdentity=function(...)
            n=n+1;if n==2 then TestAdmin.gov.base[2]=1 end;return get(...)
          end
        ''')
        self.f.run_admin(1)
        self.assertEqual(len(self.g.requests), 0)
        self.assertEqual(self.g.breakdownReads, 2)

    def test_pending_request_is_observed_before_demand_and_never_replayed(self):
        self.f.run_admin(1)
        self.assertEqual(len(self.g.requests), 1)
        reads = self.g.rateReads
        self.f.run_admin(1)
        self.assertEqual(self.g.rateReads, reads)
        self.g.Apply()
        self.g.base[1] = self.g.base[2] = 1
        self.g.breakdownReads = 0
        self.f.run_admin(1)
        self.assertEqual((self.g.breakdownReads, len(self.g.requests)), (0, 1))
        self.assertEqual(self.g.owned[930].city.GetID(), 2)

    def test_unknown_rate_or_reader_throw_is_contained_and_next_call_recovers(self):
        for value in ('nil', '0/0', 'math.huge', '-math.huge', "'unknown'", 'throw'):
            with self.subTest(value=value):
                self.setUp()
                expression = "error('unknown rate')" if value == 'throw' else value
                self.lua.execute('''local c=TestAdmin.gov.cities[2];local get=c.GetCulturalIdentity
                  P6RestoreDemand=function()c.GetCulturalIdentity=get end
                  c.GetCulturalIdentity=function(...)local ci=get(...)
                    ci.GetLoyaltyPerTurn=function()return ''' + expression + ''' end;return ci end''')
                self.f.run_admin(1)
                self.assertEqual((self.g.breakdownReads, len(self.g.requests)), (0, 0))
                self.assertGreaterEqual(len(self.f.w.requests), 2)
                self.lua.globals().P6RestoreDemand()
                self.f.run_admin(1)
                self.assertEqual(len(self.g.requests), 1)

    def demand_function(self):
        source = (ROOT/'mod/Baiqi/Lua/BaiqiAdmin.lua').read_text(encoding='utf-8')
        text = source[source.index('local function GovernorLoyaltyDemand('):source.index('local function GovernorLoyaltySnapshot(')]
        self.lua.execute(text.replace('local function GovernorLoyaltyDemand(', 'function P6TestDemand(', 1))

    def test_actual_probe_rejects_bad_counts_duplicate_roster_and_false_assignment(self):
        self.demand_function()
        self.lua.execute('''
          local p=Players[7];local get=p.GetCities;local pg=p:GetGovernors();local assigned=pg.GetAssignedGovernor
          local function rejected(own)
            p.GetCities=function()return own end
            assert(pcall(P6TestDemand,7,p,pg)==false)
          end
          for _,count in ipairs({-1,129,1.5,math.huge,0/0,'2'})do
            local own=get();own.GetCount=function()return count end;rejected(own)
          end
          local own=get();own.GetCount=function()return 1 end;rejected(own)
          own=get();local n=0;own.GetCount=function()n=n+1;return n==1 and 2 or 1 end;rejected(own)
          own=get();own.Members=function()local i=0;return function()i=i+1;if i<=2 then return i,TestAdmin.gov.cities[2]end end end
          rejected(own)
          p.GetCities=get;pg.GetAssignedGovernor=function()return false end
          assert(pcall(P6TestDemand,7,p,pg)==false)
          pg.GetAssignedGovernor=assigned
        ''')

    def test_actual_probe_caps_iteration_even_when_reported_count_is_small(self):
        self.demand_function()
        self.lua.execute('''
          local p=Players[7];local pg=p:GetGovernors();local yielded=0;local identities=0
          p.GetCities=function()return {GetCount=function()return 1 end,
            Members=function()return function()yielded=yielded+1;local id=yielded
              return id,{GetID=function()return id end,GetOwner=function()return 7 end,
                GetCulturalIdentity=function()identities=identities+1
                  return {GetLoyaltyPerTurn=function()return 1 end}end}
            end end}end
          pg.GetAssignedGovernor=function()return nil end
          assert(pcall(P6TestDemand,7,p,pg)==false and yielded==129 and identities==128)
        ''')

    def test_unknown_probe_preserves_normal_governor_fallthrough(self):
        self.lua.execute('''
          TestAdmin.gov.owned[930].city=nil
          TestAdmin.gov.cities[2].GetCulturalIdentity=function()error('unknown identity')end
        ''')
        self.f.run_admin(1)
        self.assertEqual(self.g.breakdownReads, 0)
        self.assertEqual(len(self.g.requests), 1)
        self.assertEqual(self.g.requests[1].params.city, 1)


if __name__ == '__main__':
    unittest.main()
