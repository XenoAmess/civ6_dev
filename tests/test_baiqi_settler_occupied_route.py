"""Use the real scheduler to find another safe site when a civilian blocks a step."""
from pathlib import Path
import unittest

from lupa.lua53 import LuaRuntime

ROOT = Path(__file__).resolve().parents[1]


class SettlerOccupiedRouteTests(unittest.TestCase):
    def setUp(self):
        self.lua = LuaRuntime(unpack_returned_tuples=True)
        for name in ('tests/lua/mock_world.lua', 'tests/lua/mock_movement.lua',
                     'tests/lua/mock_path_ranking.lua',
                     'mod/Baiqi/Lua/BaiqiConfig.lua',
                     'mod/Baiqi/Lua/BaiqiPolicy.lua',
                     'mod/Baiqi/Lua/BaiqiPlanner.lua',
                     'mod/Baiqi/Lua/BaiqiController.lua'):
            self.lua.execute((ROOT / name).read_text(encoding='utf-8'))
        self.lua.execute('''
            TestWorld.withSettler=true
            TestWorld.withBuilder=true
            TestWorld.builderMoves=0
            TestWorld.queueSize=1
            TestWorld.blocked={}
            TestWorld.objects.builder.GetX=function() return 3 end
            TestWorld.objects.builder.GetY=function() return 3 end
            GameInfo.Units[2].FormationClass='FORMATION_CLASS_CIVILIAN'
            local original=Units.GetUnitsInPlot
            Units.GetUnitsInPlot=function(plot)
                local id=plot:GetIndex()
                if TestWorld.blocked[id] then
                    assert(not TestWorld.fogged[id], 'hidden occupancy queried')
                    return {TestWorld.objects.builder}
                end
                return original(plot)
            end
        ''')
        self.w = self.lua.globals().TestWorld
        self.c = self.lua.globals().BaiqiController

    def requests(self):
        return [(r.unit, r.op, r.params[14], r.params[15])
                for r in self.w.unitRequests.values()]

    def run_callbacks(self, count=3):
        for _ in range(count):
            self.c.RunNow()
        self.assertNotIn('脚本错误', self.c.GetStatus())
        self.assertEqual(len(self.w.cityRequests), 0)
        self.assertFalse(any(r[0] == 1 for r in self.requests()))

    def test_blocked_first_site_uses_free_alternative_without_blocked_move(self):
        self.w.blocked[43] = True
        self.run_callbacks()
        self.assertEqual(self.requests(), [(2, 10, 2, 4)])
        self.assertEqual([q.target for q in self.w.pathQueries.values()], [46, 47])

    def test_all_first_steps_blocked_waits_without_moving_any_blocker(self):
        self.w.blocked[43], self.w.blocked[44] = True, True
        self.run_callbacks(2)
        self.assertEqual(self.requests(), [(2, 17, None, None)])
        self.assertEqual([q.target for q in self.w.pathQueries.values()], [46, 47])

    def test_own_military_stack_does_not_block_settler_or_receive_an_order(self):
        self.lua.execute('''
            local original=Units.GetUnitsInPlot
            Units.GetUnitsInPlot=function(plot)
                if plot:GetIndex()==43 then return {TestWorld.objects.army} end
                return original(plot)
            end
        ''')
        self.run_callbacks()
        self.assertEqual(self.requests(), [(2, 10, 3, 3)])

    def test_new_occupant_during_native_qualification_still_blocks_dispatch(self):
        self.lua.execute('''
            local original=UnitManager.CanStartOperation
            UnitManager.CanStartOperation=function(unit,op,mode,params)
                local result=original(unit,op,mode,params)
                if op==UnitOperationTypes.MOVE_TO then TestWorld.blocked[43]=true end
                return result
            end
        ''')
        self.run_callbacks(1)
        self.assertEqual(self.requests(), [(2, 17, None, None)])

    def test_explored_fogged_first_step_does_not_read_hidden_occupancy(self):
        self.w.blocked[43], self.w.fogged[43] = True, True
        self.run_callbacks()
        self.assertEqual(self.requests(), [(2, 10, 3, 3)])

    def test_escort_cannot_be_moved_to_reach_free_alternative(self):
        self.w.blocked[43] = True
        self.w.formation = 2
        self.run_callbacks()
        self.assertEqual(self.requests(), [])


if __name__ == '__main__':
    unittest.main()
