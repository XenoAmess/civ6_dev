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
        self.assertEqual((self.w.add[0], self.w.add[1], len(self.w.clear)), (300, 301, 0))

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


if __name__ == '__main__':
    unittest.main()
