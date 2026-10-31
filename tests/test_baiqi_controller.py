"""Controlled API doubles exercise the real adapter, not a copied implementation."""
from pathlib import Path
import unittest
from lupa.lua53 import LuaRuntime

ROOT = Path(__file__).resolve().parents[1]


class BaiqiControllerTests(unittest.TestCase):
    def setUp(self):
        self.lua = LuaRuntime(unpack_returned_tuples=True)
        self.lua.execute((ROOT / "tests/lua/mock_world.lua").read_text(encoding="utf-8"))
        for name in ("BaiqiConfig", "BaiqiPolicy", "BaiqiPlanner", "BaiqiController"):
            self.lua.execute((ROOT / f"mod/Baiqi/Lua/{name}.lua").read_text(encoding="utf-8"))
        self.world = self.lua.globals().TestWorld
        self.controller = self.lua.globals().BaiqiController

    def test_unknown_tech_exclusion_success_does_not_enqueue_locked_building(self):
        self.controller.RunNow()
        self.assertEqual(len(self.world.cityRequests), 1, self.controller.GetStatus())
        self.assertEqual(self.world.cityRequests[1][2], 101)  # Available monument, not locked granary.
        self.assertEqual(len(self.world.unitRequests), 0)

    def test_occupied_queue_never_receives_background_request(self):
        self.world.queueSize = 1
        self.controller.RunNow()
        self.assertEqual(len(self.world.cityRequests), 0)

    def test_army_only_world_has_zero_background_unit_requests(self):
        self.world.withCity = False
        for _ in range(3):
            self.world.turn += 1
            self.controller.RunNow()
        self.assertEqual(len(self.world.unitRequests), 0)

    def test_unescorted_starting_settler_founds_once(self):
        self.world.withCity, self.world.withSettler = False, True
        self.controller.RunNow()
        self.controller.RunNow()
        self.assertEqual(len(self.world.unitRequests), 1, self.controller.GetStatus())
        self.assertEqual(self.world.unitRequests[1].op, 11)
        self.assertEqual(self.world.unitRequests[1].unit, 2)

    def test_escort_is_untouched_but_old_pause_flag_cannot_disable_ai(self):
        self.world.withCity, self.world.withSettler, self.world.formation = False, True, 2
        self.controller.RunNow()
        self.assertEqual(len(self.world.unitRequests), 0)
        self.world.formation, self.world.paused = 1, True
        self.controller.RunNow()
        self.assertEqual(len(self.world.unitRequests), 1)
        self.assertEqual(self.world.unitRequests[1].op, 11)

    def test_idle_builder_skip_with_unchanged_moves_does_not_strand_next_turn(self):
        self.world.withCity, self.world.withBuilder = False, True
        self.controller.RunNow()
        self.controller.RunNow()
        self.assertEqual(len(self.world.unitRequests), 1)
        self.assertEqual((self.world.unitRequests[1].unit, self.world.unitRequests[1].op), (3, 17))
        self.world.turn += 1
        self.controller.RunNow()
        self.assertEqual(len(self.world.unitRequests), 2)
        self.assertEqual((self.world.unitRequests[2].unit, self.world.unitRequests[2].op), (3, 17))

    def movement(self):
        self.lua.execute((ROOT / 'tests/lua/mock_movement.lua').read_text(encoding='utf-8'))

    def test_unaccepted_move_becomes_normal_wait_without_same_turn_move_replay(self):
        self.movement()
        self.controller.RunNow()
        self.controller.Update(0.35)
        self.assertEqual(len(self.world.unitRequests), 1)
        self.controller.Update(0.35)
        self.assertEqual((len(self.world.unitRequests), self.world.unitRequests[2].op), (2, 17))
        self.assertEqual((self.world.builderPlot, self.world.builderMoves), (42, 2))
        self.controller.Update(2)
        self.assertEqual(len(self.world.unitRequests), 2)
        self.world.turn += 1
        self.controller.RunNow()
        self.assertEqual((len(self.world.unitRequests), self.world.unitRequests[3].op), (3, 10))

    def test_queued_busy_or_not_ready_move_is_preserved_until_actual_arrival(self):
        self.movement()
        self.controller.RunNow()
        self.world.queuedDestination = 43
        self.controller.Update(2)
        self.assertEqual(len(self.world.unitRequests), 1)
        self.world.queuedDestination, self.world.ready = None, False
        self.controller.Update(2)
        self.assertEqual(len(self.world.unitRequests), 1)
        self.world.ready, self.world.busy = True, True
        self.controller.Update(2)
        self.assertEqual(len(self.world.unitRequests), 1)
        self.world.busy, self.world.processing = False, True
        self.controller.Update(2)
        self.assertEqual(len(self.world.unitRequests), 1)
        self.world.processing, self.world.builderPlot, self.world.builderMoves = False, 43, 1
        self.controller.Update(0.35)
        self.assertEqual((len(self.world.unitRequests), self.world.unitRequests[2].op), (2, 12))

    def test_civilian_occupancy_prevents_move_while_army_stack_is_allowed(self):
        self.movement()
        self.world.targetOccupied = True
        self.controller.RunNow()
        self.assertEqual((len(self.world.unitRequests), self.world.unitRequests[1].op), (1, 17))
        self.world.targetOccupied, self.world.targetArmy = False, True
        self.world.turn += 1
        self.controller.RunNow()
        self.assertEqual((self.world.unitRequests[2].unit, self.world.unitRequests[2].op), (3, 10))

    def test_fogged_target_occupancy_is_not_read(self):
        self.movement()
        self.world.targetOccupied, self.world.visible = True, False
        self.controller.RunNow()
        self.assertEqual(self.world.plotReads, 0)
        self.assertEqual(self.world.unitRequests[1].op, 10)

    def test_builder_packet_safety_and_log_use_xy_when_plot_id_disagrees(self):
        self.movement()
        self.world.builderPlot, self.world.stalePlotId = 43, 42
        self.lua.execute('TestWorld.logs={}; print=function(s) table.insert(TestWorld.logs,s) end')
        self.controller.RunNow()
        r = self.world.unitRequests[1]
        self.assertEqual((r.op, r.params[14], r.params[15]), (12, 3, 3))
        self.assertTrue(any('operation=BUILD_IMPROVEMENT|plot=43' in line for line in self.world.logs.values()))
        self.assertNotIn('脚本错误', self.controller.GetStatus())

    def test_stale_plot_id_does_not_reject_native_path_from_actual_xy(self):
        self.movement()
        self.world.stalePlotId = 99
        self.controller.RunNow()
        self.assertEqual(self.world.unitRequests[1].op, 10)

    def test_xy_arrival_is_observed_even_with_unchanged_moves_and_stale_plot_id(self):
        self.movement()
        self.controller.RunNow()
        self.world.builderPlot, self.world.stalePlotId = 43, 42
        self.controller.Update(0.35)
        self.assertEqual([r.op for r in self.world.unitRequests.values()], [10, 12])

    def test_foreign_actual_tile_cannot_be_built_despite_owned_stale_plot(self):
        self.movement()
        self.world.builderPlot, self.world.stalePlotId = 43, 42
        self.lua.execute('Map.GetPlotByIndex(43).GetOwner=function() return 8 end')
        self.controller.RunNow()
        self.assertFalse(any(r.op == 12 for r in self.world.unitRequests.values()))

    def test_invalid_coordinates_wait_and_recover_without_native_position_call(self):
        self.movement()
        self.lua.execute('TestWorld.objects.builder.GetX=function() return nil end')
        self.controller.RunNow()
        self.assertEqual(len(self.world.unitRequests), 0)
        self.lua.execute('TestWorld.objects.builder.GetX=function() return 2 end')
        self.controller.RunNow()
        self.assertEqual(self.world.unitRequests[1].op, 10)

    def test_position_change_during_final_legality_check_cannot_submit_stale_build(self):
        self.movement()
        self.world.builderPlot = 43
        self.lua.execute('''
local original=UnitManager.CanStartOperation; local checks=0
UnitManager.CanStartOperation=function(unit,op,...)
 local allowed=original(unit,op,...)
 if op==UnitOperationTypes.BUILD_IMPROVEMENT then
  checks=checks+1
  if checks==2 then TestWorld.builderPlot=42 end
 end
 return allowed
end
''')
        self.controller.RunNow()
        self.assertFalse(any(r.op == 12 for r in self.world.unitRequests.values()))

    def test_pending_move_with_unknown_coordinates_waits_for_valid_position(self):
        self.movement()
        self.controller.RunNow()
        self.lua.execute('TestWorld.objects.builder.GetX=function() return nil end')
        self.controller.Update(2)
        self.assertEqual(len(self.world.unitRequests), 1)
        self.world.builderPlot = 43
        self.lua.execute('TestWorld.objects.builder.GetX=function() return 3 end')
        self.controller.RunNow()
        self.assertEqual([r.op for r in self.world.unitRequests.values()], [10, 12])

    def test_recycled_unit_lookup_does_not_report_old_move_as_observed(self):
        self.movement()
        self.controller.RunNow()
        self.lua.execute('''
TestWorld.logs={};print=function(s) table.insert(TestWorld.logs,s) end
TestWorld.objects.builder.GetID=function() return 65539 end
TestWorld.objects.builder.GetFormationUnitCount=function() return 2 end
local original=TestWorld.objects.player.GetUnits
TestWorld.objects.player.GetUnits=function(self)
 local units=original(self);units.FindID=function() return TestWorld.objects.builder end;return units
end
''')
        self.controller.Update(0.35)
        logs = list(self.world.logs.values())
        self.assertTrue(any('reason=unit_unavailable' in s for s in logs))
        self.assertFalse(any('BAIQI|observed|' in s for s in logs))
        self.assertEqual(len(self.world.unitRequests), 1)


if __name__ == "__main__":
    unittest.main()
