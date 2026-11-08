"""Intervene before a new city's loyalty falls, with safe reassignment limits."""
from pathlib import Path
import unittest

from tests import test_baiqi_governor_loyalty as existing

ROOT = Path(__file__).resolve().parents[1]


class EarlyGovernorLoyaltyTests(unittest.TestCase):
    planner_source = None
    admin_source = None

    def setUp(self):
        self.fixture = existing.GovernorLoyaltyConsumerTests(methodName='runTest')
        self.fixture.setUp()
        self.lua, self.g = self.fixture.lua, self.fixture.g
        if self.planner_source is not None:
            self.lua.execute(self.planner_source)
        if self.admin_source is not None:
            self.lua.execute(self.admin_source)
            self.fixture.admin = self.lua.globals().BaiqiAdmin
        self.g.loyalty[2] = 100
        self.g.base[2] = -2.6875

    def run_admin(self, count=2):
        self.fixture.run_admin(count)

    def test_full_loyalty_negative_city_gets_one_safe_assignment_then_observed_effect(self):
        self.run_admin()
        self.assertEqual(len(self.g.requests), 1)
        self.assertEqual(self.g.requests[1].params.city, 2)
        self.assertEqual(self.g.owned[930].city.GetID(), 1)
        self.g.Apply()
        self.run_admin()
        self.assertEqual(self.g.owned[930].city.GetID(), 2)
        self.assertEqual(self.g.cities[2].GetCulturalIdentity().GetLoyaltyPerTurn(), 5.3125)
        self.assertEqual(self.g.cities[1].GetCulturalIdentity().GetLoyaltyPerTurn(), 21)
        self.assertEqual((len(self.g.requests), self.g.spent), (1, 6))

    def test_small_negative_rate_does_not_wait_for_loyalty_loss(self):
        self.g.base[2] = -0.001
        self.run_admin()
        self.assertEqual(len(self.g.requests), 1)

    def test_old_76_threshold_now_receives_safe_help(self):
        self.g.loyalty[2] = 76
        self.run_admin()
        self.assertEqual(len(self.g.requests), 1)

    def test_zero_or_positive_rate_keeps_governor(self):
        for rate in (0, 0.3125):
            with self.subTest(rate=rate):
                self.setUp()
                self.g.base[2] = rate
                self.run_admin()
                self.assertEqual(len(self.g.requests), 0)

    def test_one_governor_must_make_target_strictly_positive(self):
        for rate in (-8, -9.5625):
            with self.subTest(rate=rate):
                self.setUp()
                self.g.base[2] = rate
                self.run_admin()
                self.assertEqual(len(self.g.requests), 0)

    def test_new_city_does_not_take_unsafe_donor_governor(self):
        for field, value in (('loyalty', 79), ('base', 0)):
            with self.subTest(field=field):
                self.setUp()
                getattr(self.g, field)[1] = value
                self.run_admin()
                self.assertEqual(len(self.g.requests), 0)

    def test_full_loyalty_target_worsening_at_final_permission_stops_request(self):
        self.lua.execute('''TestAdmin.gov.onPermission=function(n)
            if n==3 then TestAdmin.gov.base[2]=-20 end end''')
        self.run_admin(1)
        self.assertEqual(len(self.g.requests), 0)

    def test_early_false_ack_is_not_replayed_next_turn(self):
        self.g.requestFalse = True
        self.run_admin()
        self.fixture.w.turn = 2
        self.run_admin()
        self.assertEqual(len(self.g.requests), 1)


if __name__ == '__main__':
    unittest.main()
