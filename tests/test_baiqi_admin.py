from pathlib import Path
import unittest
from lupa.lua53 import LuaRuntime

ROOT = Path(__file__).resolve().parents[1]


class AdministrationTests(unittest.TestCase):
    def setUp(self):
        self.lua = LuaRuntime(unpack_returned_tuples=True)
        self.lua.execute((ROOT / 'tests/lua/mock_admin.lua').read_text(encoding='utf-8'))
        for name in ('BaiqiConfig', 'BaiqiAdmin'):
            self.lua.execute((ROOT / f'mod/Baiqi/Lua/{name}.lua').read_text(encoding='utf-8'))
        self.w, self.admin = self.lua.globals().TestAdmin, self.lua.globals().BaiqiAdmin

    def test_normal_research_path_payloads_and_one_attempt_per_item_per_turn(self):
        self.admin.Run()
        self.admin.Run()
        self.assertEqual(len(self.w.requests), 2)
        self.assertEqual(self.w.requests[1].params.tech[1], 100)
        self.assertEqual(self.w.requests[2].params.civic[1], 200)
        self.assertEqual(self.w.requests[1].params.mode, 3)

    def test_policy_slots_are_zero_based_hash_map_without_signature_guessing(self):
        self.admin.Run()
        self.assertEqual(self.w.policyCalls, 1)
        self.assertEqual((self.w.add[0], self.w.add[1], self.w.clear[1], self.w.clear[2]), (300, 301, 0, 1))
        self.assertEqual((self.w.slots[1], self.w.slots[2]), (0, 1))

    def test_complete_policy_batch_preserves_existing_policy_while_filling_empty_slot(self):
        self.w.slots[1] = 0
        self.admin.Run()
        self.assertEqual((self.w.add[0], self.w.add[1]), (300, 301))
        self.assertEqual((self.w.slots[1], self.w.slots[2]), (0, 1))

    def test_active_queues_and_existing_policies_are_preserved(self):
        self.w.tech, self.w.civic = 0, 0
        self.w.slots[1], self.w.slots[2] = 0, 1
        self.admin.Run()
        self.assertEqual((len(self.w.requests), self.w.policyCalls), (0, 0))

    def test_other_leader_inactive_turn_and_policy_change_gate(self):
        self.w.leader = 'LEADER_TRAJAN'
        self.admin.Run()
        self.assertEqual(len(self.w.requests), 0)
        self.w.leader, self.w.active = 'LEADER_BAIQI', False
        self.admin.Run()
        self.assertEqual(len(self.w.requests), 0)
        self.w.active, self.w.policyChanged = True, True
        self.admin.Run()
        self.assertEqual((len(self.w.requests), self.w.policyCalls), (2, 0))

    def governors(self):
        self.lua.execute((ROOT / 'tests/lua/mock_governors.lua').read_text(encoding='utf-8'))
        # Governor handling must also run outside the free policy-change window.
        self.w.policyChanged = True
        return self.w.gov

    def test_governor_requests_wait_for_state_and_spend_real_titles(self):
        g = self.governors()
        self.admin.Run()
        self.admin.Run()
        self.assertEqual((len(g.requests), g.spent), (1, 0))
        g.Apply()
        self.assertEqual(g.spent, 1)
        self.admin.Run()
        self.admin.Run()
        self.assertEqual(len(g.requests), 2)
        g.Apply()
        self.assertEqual(g.owned[930].city.GetID(), 2)
        self.admin.Run()
        g.Apply()
        self.assertEqual((g.spent, g.owned[930].promoted), (2, True))
        self.admin.Run()
        self.assertEqual(len(g.requests), 3)

    def test_governor_no_titles_and_base_game_absence(self):
        g = self.governors()
        g.points = 0
        self.admin.Run()
        self.assertEqual(len(g.requests), 0)
        self.lua.execute('Players[7].GetGovernors=nil;GameInfo.Governors=nil')
        self.admin.Run()
        self.assertEqual(len(g.requests), 0)

    def test_governor_rejects_illegal_city_and_preserves_existing_assignment(self):
        g = self.governors()
        self.admin.Run()
        g.Apply()
        g.illegal[2] = True
        self.admin.Run()
        g.Apply()
        self.assertEqual(g.owned[930].city.GetID(), 1)
        self.admin.Run()
        g.Apply()
        self.w.turn = 2
        self.admin.Run()
        self.assertEqual(g.owned[930].city.GetID(), 1)
        self.assertEqual(len(g.requests), 3)

    def test_neutralized_governor_is_not_assigned(self):
        g = self.governors()
        self.admin.Run()
        g.Apply()
        g.points, g.neutralized = 1, 2
        self.admin.Run()
        self.assertEqual(len(g.requests), 1)

    def pantheon(self):
        self.lua.execute((ROOT / 'tests/lua/mock_pantheon.lua').read_text(encoding='utf-8'))
        self.w.policyChanged = True
        return self.w.faith

    def test_pantheon_hash_request_waits_for_real_consumer_and_charges_normal_faith(self):
        f = self.pantheon()
        self.admin.Run()
        self.admin.Run()
        self.assertEqual((len(f.requests), f.balance, f.pantheon), (1, 50, -1))
        self.assertEqual(f.requests[1].belief, 505)
        f.Apply()
        self.assertEqual((f.balance, f.pantheon), (25, 5))
        self.w.turn = 2
        self.admin.Run()
        self.assertEqual(len(f.requests), 1)

    def test_pantheon_excludes_beliefs_claimed_in_pantheon_or_religion(self):
        f = self.pantheon()
        f.inReligion[5] = True
        self.admin.Run()
        self.assertEqual(f.requests[1].belief, 502)
        f.claimed[2] = True
        self.admin.Run()
        self.w.turn = 2
        self.admin.Run()
        self.assertEqual(len(f.requests), 1)

    def test_pantheon_does_not_retry_another_belief_before_pending_confirmation(self):
        f = self.pantheon()
        self.admin.Run()
        f.claimed[5] = True
        self.admin.Run()
        self.assertEqual(len(f.requests), 1)

    def test_pantheon_requires_native_permission_faith_and_correct_leader(self):
        f = self.pantheon()
        f.can = False
        self.admin.Run()
        f.can, f.balance = True, 24
        self.admin.Run()
        f.balance, self.w.leader = 50, 'LEADER_TRAJAN'
        self.admin.Run()
        self.assertEqual(len(f.requests), 0)

    def government(self):
        self.lua.execute((ROOT / 'tests/lua/mock_government.lua').read_text(encoding='utf-8'))
        return self.w.government

    def test_government_upgrades_normal_hash_request_and_waits_for_state(self):
        g = self.government()
        self.admin.Run()
        self.admin.Run()
        self.assertEqual((len(g.requests), g.requests[1], g.current), (1, 702, 0))
        self.assertEqual(self.w.policyCalls, 0)
        g.Apply()
        self.admin.Run()
        self.assertEqual((g.current, self.w.policyCalls), (2, 1))
        self.assertEqual(len(g.requests), 1)

    def test_government_rejects_paid_anarchy_locked_or_same_tier_changes(self):
        g = self.government()
        g.free = False
        self.admin.Run()
        self.assertEqual(len(g.requests), 0)
        g.free = True
        g.anarchy[1], g.anarchy[2] = 2, 2
        self.admin.Run()
        self.assertEqual(len(g.requests), 0)
        g.anarchy[1], g.anarchy[2], g.current = None, None, 1
        self.admin.Run()
        self.assertEqual(len(g.requests), 0)

    def test_government_retains_current_only_after_evaluating_no_upgrade(self):
        g = self.government()
        g.current, g.blocker = 2, 88
        self.admin.Run()
        self.assertTrue(g.retained)
        self.assertEqual(len(g.requests), 0)

    def test_dedication_normal_choice_waits_for_actual_state_and_uses_index(self):
        self.lua.execute((ROOT / 'tests/lua/mock_dedication.lua').read_text(encoding='utf-8'))
        e = self.w.era
        self.admin.Run()
        self.admin.Run()
        self.assertEqual((len(e.requests), e.requests[1], len(e.active)), (1, 2, 0))
        e.Apply()
        self.admin.Run()
        self.assertEqual((len(e.requests), e.active[1]), (1, 2))

    def test_heroic_dedications_complete_for_total_or_remaining_native_counter(self):
        for remaining in (False, True):
            with self.subTest(remaining=remaining):
                self.setUp()
                self.lua.execute((ROOT / 'tests/lua/mock_dedication.lua').read_text(encoding='utf-8'))
                e = self.w.era
                e.allowed, e.remaining = 3, remaining
                for expected in (2, 0, 1):
                    self.admin.Run()
                    self.admin.Run()
                    self.assertEqual(e.requests[len(e.requests)], expected)
                    e.Apply()
                self.admin.Run()
                self.assertEqual((len(e.requests), len(e.active)), (3, 3))

    def test_great_people_recruitment_waits_for_confirmation_and_spends_points(self):
        self.lua.execute((ROOT / 'tests/lua/mock_great_people.lua').read_text(encoding='utf-8'))
        p = self.w.people
        self.admin.Run()
        self.admin.Run()
        self.assertEqual((len(p.requests), len(p.units), p.points), (1, 0, 120))
        p.Apply()
        self.admin.Run()
        self.admin.Run()
        self.assertEqual((len(p.requests), len(p.units), p.points), (2, 1, 60))
        p.Apply()
        self.admin.Run()
        self.assertEqual((len(p.requests), len(p.units), p.points), (2, 2, 0))

    def test_great_people_insufficient_points_do_not_trigger_patronage(self):
        self.lua.execute((ROOT / 'tests/lua/mock_great_people.lua').read_text(encoding='utf-8'))
        self.w.people.points = 59
        self.admin.Run()
        self.assertEqual(len(self.w.people.requests), 0)


if __name__ == '__main__':
    unittest.main()
