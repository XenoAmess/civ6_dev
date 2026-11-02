"""Exercise real controller path reads and uncached command boundaries."""
from pathlib import Path
import unittest

from lupa.lua53 import LuaRuntime

ROOT = Path(__file__).resolve().parents[1]


class PathSafetyCacheTests(unittest.TestCase):
    def setUp(self):
        self.lua = LuaRuntime(unpack_returned_tuples=True)
        for name in ('tests/lua/mock_world.lua', 'tests/lua/mock_movement.lua',
                     'tests/lua/mock_path_ranking.lua', 'mod/Baiqi/Lua/BaiqiConfig.lua',
                     'mod/Baiqi/Lua/BaiqiPolicy.lua', 'mod/Baiqi/Lua/BaiqiPlanner.lua'):
            self.lua.execute((ROOT / name).read_text(encoding='utf-8'))
        source = (ROOT / 'mod/Baiqi/Lua/BaiqiController.lua').read_text(encoding='utf-8')
        self.private = self.lua.execute(source + '\nreturn {Safe=Safe,PathStep=PathStep}\n')
        self.w = self.lua.globals().TestWorld
        self.c = self.lua.globals().BaiqiController
        self.c.RunNow(False)
        self.assertEqual(len(self.w.unitRequests), 0)

    def path(self):
        g = self.lua.globals()
        return self.private.PathStep(self.w.objects.settler, g.Map.GetPlotByIndex(46),
                                     self.w.objects.player, self.lua.table())

    def test_each_visible_cell_is_read_once_per_path_plus_target_precheck(self):
        self.lua.execute('''
            TestWorld.cellReads={}
            local original=Units.GetUnitsInPlot
            Units.GetUnitsInPlot=function(plot)
                local id=plot:GetIndex()
                TestWorld.cellReads[id]=(TestWorld.cellReads[id] or 0)+1
                return original(plot)
            end
        ''')
        self.assertEqual(self.path().GetIndex(), 43)
        reads = list(self.w.cellReads.values())
        self.assertGreater(len(reads), 5)
        self.assertLessEqual(max(reads), 2)

    def test_enemy_changes_between_path_calls_are_observed(self):
        self.assertEqual(self.path().GetIndex(), 43)
        self.w.enemyPlot = 43
        self.assertIsNone(self.path())

    def test_path_query_cannot_reuse_earlier_target_safety(self):
        self.lua.execute('''
            local original=UnitManager.GetMoveToPathEx
            UnitManager.GetMoveToPathEx=function(...)
                local result=original(...)
                TestWorld.enemyPlot=62
                return result
            end
        ''')
        self.assertIsNone(self.path())

    def mutation_before_write(self, assignment):
        self.w.withBuilder, self.w.withSettler = False, True
        self.lua.execute('''
            TestWorld.settlementRecommendations={46}
            local original=Map.GetPlotByIndex
            local reads=0
            Map.GetPlotByIndex=function(id)
                if id==43 then
                    reads=reads+1
                    if reads==2 then MUTATION end
                end
                return original(id)
            end
        '''.replace('MUTATION', assignment))
        self.c.RunNow()
        self.assertGreaterEqual(len(self.w.pathQueries), 1)
        for request in self.w.unitRequests.values():
            self.assertNotEqual(request.unit, 1)
            self.assertNotEqual(request.op, 10)

    def test_enemy_after_planning_is_reread_before_move(self):
        self.mutation_before_write('TestWorld.enemyPlot=43')

    def test_visibility_after_planning_is_reread_before_move(self):
        self.mutation_before_write('TestWorld.hidden[43]=true')

    def test_malformed_cache_value_is_not_a_safe_result(self):
        cache = self.lua.table()
        for index in (42, 43, 44, 45, 46, 47, 48, 50, 60, 61, 62, 70, 71, 72, 73, 74):
            cache[index] = 'unknown'
        self.w.enemyPlot = 43
        g = self.lua.globals()
        self.assertFalse(self.private.Safe(g.Map.GetPlotByIndex(43), self.w.objects.player, cache))

    def test_unavailable_layer_is_not_retained_as_a_known_threat(self):
        self.lua.execute('''
            TestWorld.originalReligious=Units.GetUnitsInPlotLayerID
            Units.GetUnitsInPlotLayerID=function(plot,layer)
                if plot:GetIndex()==43 then return nil end
                return TestWorld.originalReligious(plot,layer)
            end
        ''')
        g, cache = self.lua.globals(), self.lua.table()
        plot = g.Map.GetPlotByIndex(43)
        self.assertFalse(self.private.Safe(plot, self.w.objects.player, cache))
        self.lua.execute('Units.GetUnitsInPlotLayerID=TestWorld.originalReligious')
        self.assertTrue(self.private.Safe(plot, self.w.objects.player, cache))

    def test_default_safety_checks_have_no_cache(self):
        g = self.lua.globals()
        plot = g.Map.GetPlotByIndex(43)
        self.assertTrue(self.private.Safe(plot, self.w.objects.player))
        self.w.enemyPlot = 43
        self.assertFalse(self.private.Safe(plot, self.w.objects.player))


if __name__ == '__main__':
    unittest.main()
