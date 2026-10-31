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


if __name__ == "__main__":
    unittest.main()
