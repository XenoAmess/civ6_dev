"""Native-shaped rejected wait and actual path/arrival, without military orders."""
from pathlib import Path
import unittest
from lupa.lua53 import LuaRuntime
from gp_intent_harness import install_gp_bridge

ROOT = Path(__file__).resolve().parents[1]


class CivilianOverlapTests(unittest.TestCase):
    def setUp(self):
        self.lua = LuaRuntime(unpack_returned_tuples=True)
        self.lua.execute((ROOT/'tests/lua/mock_world.lua').read_text(encoding='utf-8'))
        install_gp_bridge(self.lua)
        for path in ('tests/lua/mock_scientist.lua',
                     'tests/lua/mock_civilian_overlap.lua', 'mod/Baiqi/Lua/BaiqiConfig.lua',
                     'mod/Baiqi/Lua/BaiqiPolicy.lua', 'mod/Baiqi/Lua/BaiqiPlanner.lua',
                     'mod/Baiqi/Lua/BaiqiController.lua'):
            self.lua.execute((ROOT/path).read_text(encoding='utf-8'))
        self.w, self.c = self.lua.globals().TestWorld, self.lua.globals().BaiqiController

    def test_rejected_wait_unstacks_only_civilian_then_arrival_allows_normal_wait(self):
        self.c.RunNow()
        self.assertEqual((self.w.unitRequests[1].unit, self.w.unitRequests[1].op), (4, 10))
        self.assertEqual((self.w.unitRequests[1].params[14], self.w.unitRequests[1].params[15]), (3, 3))
        self.w.scientistPlot, self.w.overlap, self.w.allowWait = 43, False, True
        self.c.Update(0.35)
        self.assertEqual([r.op for r in self.w.unitRequests.values()], [10, 17])
        self.w.turn += 1
        self.c.RunNow()
        self.assertEqual([r.op for r in self.w.unitRequests.values()], [10, 17, 17])

    def test_native_wait_succeeds_without_relocation_even_when_overlapped(self):
        self.w.allowWait = True
        self.c.RunNow()
        self.assertEqual([r.op for r in self.w.unitRequests.values()], [17])

    def test_unstacked_army_only_and_escorted_units_never_roam(self):
        for flag in ('no_overlap', 'army_only', 'formation'):
            with self.subTest(flag=flag):
                self.setUp()
                if flag == 'no_overlap':
                    self.w.overlap = False
                elif flag == 'army_only':
                    self.w.armyOnly = True
                else:
                    self.w.scientistFormation = 2
                self.c.RunNow()
                self.assertEqual(len(self.w.unitRequests), 0)

    def test_foreign_hidden_occupied_water_mountain_empty_path_and_native_rejection_wait(self):
        for flag in ('foreignTarget', 'hiddenTarget', 'occupiedTarget', 'water', 'impassable', 'noPath', 'rejectMove'):
            with self.subTest(flag=flag):
                self.setUp()
                self.w[flag] = True
                self.c.RunNow()
                self.assertEqual(len(self.w.unitRequests), 0)
                if flag == 'hiddenTarget':
                    self.assertEqual(self.w.parkingReads, 0)

    def test_pending_destination_reservation_survives_turn_and_prevents_competing_move(self):
        self.w.secondCivilian, self.w.queuedDestination = True, 43
        self.c.RunNow(); self.c.RunNow()
        self.assertEqual(len(self.w.unitRequests), 1)
        self.w.turn += 1
        self.c.Update(3)
        self.c.RunNow()
        self.assertEqual(len(self.w.unitRequests), 1)

    def test_inactive_and_other_leader_never_send_relocation(self):
        self.w.strategic = False
        self.c.RunNow()
        self.w.strategic = True
        self.lua.execute("PlayerConfigurations[7].GetLeaderTypeName=function() return 'LEADER_TRAJAN' end")
        self.c.RunNow()
        self.assertEqual(len(self.w.unitRequests), 0)

    def test_formation_change_at_final_native_legality_cannot_move_escorted_army(self):
        self.lua.execute('''
local original=UnitManager.CanStartOperation
UnitManager.CanStartOperation=function(unit,op,...)
 local legal=original(unit,op,...)
 if op==UnitOperationTypes.MOVE_TO then TestWorld.scientistFormation=2 end
 return legal
end
''')
        self.c.RunNow()
        self.assertEqual(len(self.w.unitRequests), 0)


if __name__ == '__main__':
    unittest.main()
