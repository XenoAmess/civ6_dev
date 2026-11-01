"""Earned religion decisions use native payloads and actual staged readback."""
from pathlib import Path
import unittest
from lupa.lua53 import LuaRuntime

ROOT = Path(__file__).resolve().parents[1]


class ReligionTests(unittest.TestCase):
    def setUp(self):
        self.lua = LuaRuntime(unpack_returned_tuples=True)
        for file in ('tests/lua/mock_admin.lua', 'tests/lua/mock_religion.lua',
                     'mod/Baiqi/Lua/BaiqiConfig.lua', 'mod/Baiqi/Lua/BaiqiAdmin.lua'):
            self.lua.execute((ROOT/file).read_text(encoding='utf-8'))
        self.w = self.lua.globals().TestAdmin
        self.r, self.admin = self.w.religion, self.lua.globals().BaiqiAdmin
        self.w.tech, self.w.civic, self.w.policyChanged = 0, 0, True
        self.logs = []
        self.lua.globals().print = lambda *args: self.logs.append(' '.join(map(str, args)))

    def test_earned_foundation_and_two_beliefs_wait_for_native_state_each_stage(self):
        self.admin.Run()
        self.admin.Run()
        self.assertEqual((len(self.r.requests), self.r.id), (1, -1))
        self.assertEqual(self.r.requests[1].params.religion, 502)
        self.r.Apply()
        self.admin.Run()
        self.admin.Run()
        self.assertEqual((len(self.r.requests), len(self.r.beliefs)), (2, 0))
        self.assertEqual(self.r.requests[2].params.belief, 600)
        self.r.Apply()
        self.admin.Run()
        self.assertEqual(self.r.requests[3].params.belief, 601)
        self.r.Apply()
        self.admin.Run()
        self.assertEqual((self.r.id, self.r.earned, len(self.r.beliefs), len(self.r.requests)), (2, 2, 2, 3))
        self.assertEqual(sum('BAIQI|admin_observed' in line for line in self.logs), 3)

    def test_no_earned_capacity_missing_pantheon_or_other_leader_never_founds(self):
        for field, value in (('earned', 0), ('pantheon', -1)):
            with self.subTest(field=field):
                self.setUp()
                self.r[field] = value
                self.admin.Run()
                self.assertEqual(len(self.r.requests), 0)
        self.setUp()
        self.w.leader = 'LEADER_TRAJAN'
        self.admin.Run()
        self.assertEqual(len(self.r.requests), 0)

    def test_custom_religion_fallback_has_required_explicit_name(self):
        self.r.found[2] = True
        self.admin.Run()
        self.assertEqual(self.r.requests[1].params.religion, 500)
        self.assertEqual(self.r.requests[1].params.custom, '白绮之道')
        self.r.Apply()
        self.assertEqual(self.r.id, 0)

    def test_existing_follower_and_earned_capacity_preserved_and_distinct_class_added(self):
        self.r.id = 2
        self.r.beliefs[1], self.r.claimed[0] = 0, True
        self.admin.Run()
        self.assertEqual((len(self.r.requests), self.r.requests[1].op, self.r.requests[1].params.belief), (1, 51, 601))
        self.r.Apply()
        self.admin.Run()
        self.assertEqual((len(self.r.requests), self.r.beliefs[1], len(self.r.beliefs)), (1, 0, 2))

    def test_global_occupancy_class_and_native_limit_filter_before_request(self):
        self.r.id = 2
        self.r.claimed[0] = True
        self.admin.Run()
        self.assertEqual(self.r.requests[1].params.belief, 604)
        self.r.Apply()
        self.r.forbidden[1] = True
        self.admin.Run()
        self.assertEqual(self.r.requests[2].params.belief, 602)
        self.r.Apply()
        self.admin.Run()
        self.assertEqual(len(self.r.requests), 2)

    def test_pending_unrelated_state_change_never_clears_correlation_or_repeats(self):
        self.admin.Run()
        self.r.id = 0
        for turn in range(2, 6):
            self.w.turn = turn
            self.admin.Run()
        self.assertEqual(len(self.r.requests), 1)
        self.assertEqual(sum('religion_request_pending' in line for line in self.logs), 1)
        self.r.id = -1
        self.r.Apply()
        self.admin.Run()
        self.assertEqual((len(self.r.requests), self.r.requests[2].params.belief), (2, 600))

    def test_changed_earned_capacity_at_final_read_prevents_dispatch(self):
        self.lua.execute('''
local original=Players[7].GetReligion;local reads=0
Players[7].GetReligion=function(self)
 local obj=original(self)
 obj.GetNumBeliefsEarned=function() reads=reads+1;return reads>1 and 0 or 2 end
 return obj
end
''')
        self.admin.Run()
        self.assertEqual(len(self.r.requests), 0)

    def test_missing_native_religion_list_waits_and_recovers_without_fake_decision(self):
        self.r.id, self.r.missingList = 2, True
        self.admin.Run()
        self.assertEqual(len(self.r.requests), 0)
        self.r.missingList = False
        self.admin.Run()
        self.assertEqual((len(self.r.requests), self.r.requests[1].params.belief), (1, 600))

    def test_context_change_during_final_native_eligibility_prevents_write(self):
        self.lua.execute('''
local world=Game.GetReligion();local original=world.HasBeenFounded;local calls=0
world.HasBeenFounded=function(...)
 calls=calls+1
 if calls==3 then TestAdmin.leader='LEADER_TRAJAN' end
 return original(...)
end
''')
        self.admin.Run()
        self.assertEqual(len(self.r.requests), 0)


if __name__ == '__main__':
    unittest.main()
