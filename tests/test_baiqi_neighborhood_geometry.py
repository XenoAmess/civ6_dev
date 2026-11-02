"""Cache immutable native topology while re-reading every live safety fact."""
from pathlib import Path
import unittest

from lupa.lua53 import LuaRuntime

ROOT = Path(__file__).resolve().parents[1]


class NeighborhoodGeometryTests(unittest.TestCase):
    def setUp(self):
        self.lua = LuaRuntime(unpack_returned_tuples=True)
        for name in ('tests/lua/mock_world.lua', 'tests/lua/mock_movement.lua',
                     'tests/lua/mock_path_ranking.lua', 'mod/Baiqi/Lua/BaiqiConfig.lua',
                     'mod/Baiqi/Lua/BaiqiPolicy.lua', 'mod/Baiqi/Lua/BaiqiPlanner.lua'):
            self.lua.execute((ROOT / name).read_text(encoding='utf-8'))
        self.lua.execute('''
            TestWorld.geometryCalls=0
            Events.LoadGameViewStateDone={
                Add=function(fn) TestWorld.geometryWorldReady=fn end,
                Remove=function(fn) if TestWorld.geometryWorldReady==fn then TestWorld.geometryWorldReady=nil end end}
            local original=Map.GetPlotXYWithRangeCheck
            Map.GetPlotXYWithRangeCheck=function(...)
                TestWorld.geometryCalls=TestWorld.geometryCalls+1
                return original(...)
            end
        ''')
        source = (ROOT / 'mod/Baiqi/Lua/BaiqiController.lua').read_text(encoding='utf-8')
        self.private = self.lua.execute(source + '\nreturn {Safe=Safe,Geometry=NeighborhoodGeometry}\n')
        self.w = self.lua.globals().TestWorld
        self.lua.globals().BaiqiController.RunNow(False)

    def safe(self, index=42, cache=None):
        return self.private.Safe(self.lua.globals().Map.GetPlotByIndex(index), self.w.objects.player, cache)

    def geometry(self, index=42, radius=2):
        result = self.private.Geometry(self.lua.globals().Map.GetPlotByIndex(index), radius)
        # Geometry may also return its internal invalidation key.
        return result[0] if isinstance(result, tuple) else result

    def test_repeat_footprint_saves_native_queries_but_still_detects_new_enemy(self):
        self.assertTrue(self.safe())
        cold = self.w.geometryCalls
        self.assertGreater(cold, 0)
        self.assertTrue(self.safe())
        self.assertEqual(self.w.geometryCalls, cold)
        self.w.enemyPlot = 43
        self.assertFalse(self.safe())
        self.assertEqual(self.w.geometryCalls, cold)

    def test_invisible_neighbor_is_skipped_without_reading_hidden_units(self):
        self.w.fogged[43] = True
        self.w.enemyPlot = 43
        self.assertTrue(self.safe())

    def test_known_boolean_still_checks_each_neighbors_current_visibility(self):
        cache = self.lua.table()
        self.assertTrue(self.safe(cache=cache))
        self.lua.execute('''
            TestWorld.neighborVisibilityReads=0
            local original=PlayersVisibility[7].IsVisible
            PlayersVisibility[7].IsVisible=function(self,x,y)
                if x==3 and y==3 then TestWorld.neighborVisibilityReads=TestWorld.neighborVisibilityReads+1 end
                return original(self,x,y)
            end
        ''')
        self.assertTrue(self.safe(cache=cache))
        self.assertGreater(self.w.neighborVisibilityReads, 0)

    def test_binding_change_invalidates_all_previously_warm_centers(self):
        self.lua.execute('''
            local a,b=Map.GetPlotByIndex(42),Map.GetPlotByIndex(43)
            local oldNeighbor,newNeighbor=Map.GetPlotByIndex(60),Map.GetPlotByIndex(61)
            TestWorld.geometryA=a;TestWorld.geometryB=b
            local function oracle(neighbor)
                return function(x,y,dx,dy,r)
                    if dx==0 and dy==0 then return x==a:GetX() and a or b end
                    if dx==1 and dy==0 then return neighbor end
                end
            end
            Map.GetPlotXYWithRangeCheck=oracle(oldNeighbor)
            TestWorld.newGeometryBinding=oracle(newNeighbor)
        ''')
        self.geometry(42, 1)
        self.geometry(43, 1)
        self.lua.execute('Map.GetPlotXYWithRangeCheck=TestWorld.newGeometryBinding')
        self.assertIn(61, [p.index for p in self.geometry(42, 1).values()])
        second = [p.index for p in self.geometry(43, 1).values()]
        self.assertIn(61, second)
        self.assertNotIn(60, second)

    def test_center_index_is_part_of_key_even_with_same_coordinates(self):
        self.lua.execute('''
            local center=Map.GetPlotByIndex(42)
            TestWorld.geometryCenter=center
            Map.GetPlotXYWithRangeCheck=function(x,y,dx,dy,r)
                if dx==0 and dy==0 then return TestWorld.geometryCenter end
            end
        ''')
        self.assertEqual(self.geometry(42, 0)[1].index, 42)
        self.lua.execute('''
            TestWorld.geometryCenter={GetIndex=function() return 1042 end,
                GetX=function() return 2 end,GetY=function() return 3 end}
        ''')
        result = self.private.Geometry(self.w.geometryCenter, 0)
        rows = result[0] if isinstance(result, tuple) else result
        self.assertEqual(rows[1].index, 1042)

    def test_capacity_is_bounded_for_string_keys(self):
        self.lua.execute('''
            TestWorld.geometryCenters={};TestWorld.geometryCalls=0
            for i=1,257 do
                local n=i
                TestWorld.geometryCenters[i]={GetIndex=function() return 2000+n end,
                    GetX=function() return n end,GetY=function() return 0 end}
            end
            Map.GetPlotXYWithRangeCheck=function(x,y,dx,dy,r)
                TestWorld.geometryCalls=TestWorld.geometryCalls+1
                if dx==0 and dy==0 then return TestWorld.geometryCenters[x] end
            end
        ''')
        for index in range(1, 258):
            self.private.Geometry(self.w.geometryCenters[index], 0)
        before = self.w.geometryCalls
        self.private.Geometry(self.w.geometryCenters[1], 0)
        self.assertGreater(self.w.geometryCalls, before)

    def test_native_range_and_wrap_result_defines_actual_footprint(self):
        self.lua.execute('''
            local center,wrapped=Map.GetPlotByIndex(42),Map.GetPlotByIndex(46)
            Map.GetPlotXYWithRangeCheck=function(x,y,dx,dy,r)
                if dx==0 and dy==0 then return center end
                if dx==1 and dy==0 then return wrapped end
            end
        ''')
        self.assertEqual({p.index for p in self.geometry().values()}, {42, 46})
        self.assertTrue(self.safe())
        self.w.enemyPlot = 46
        self.assertFalse(self.safe())

    def test_missing_center_does_not_make_partial_geometry_authoritative(self):
        self.lua.execute('''
            local neighbor=Map.GetPlotByIndex(43)
            Map.GetPlotXYWithRangeCheck=function(x,y,dx,dy,r)
                if dx==1 and dy==0 then return neighbor end
            end
        ''')
        self.assertIsNone(self.geometry())
        self.assertFalse(self.safe())

    def test_enumeration_error_is_unknown_and_is_not_cached(self):
        self.lua.execute('''
            local original=Map.GetPlotXYWithRangeCheck
            TestWorld.geometryBroken=true
            Map.GetPlotXYWithRangeCheck=function(...)
                if TestWorld.geometryBroken then error('native topology unavailable') end
                return original(...)
            end
        ''')
        self.assertIsNone(self.geometry())
        self.w.geometryBroken = False
        self.assertIsNotNone(self.geometry())

    def test_missing_binding_is_unknown(self):
        self.lua.execute('Map.GetPlotXYWithRangeCheck=nil')
        self.assertIsNone(self.geometry())
        self.assertFalse(self.safe())

    def test_wrong_resolved_plot_fails_closed_and_can_recover(self):
        self.assertTrue(self.safe())
        self.lua.execute('''
            local original=Map.GetPlotByIndex
            TestWorld.badGeometryLookup=true
            Map.GetPlotByIndex=function(index)
                if index==43 and TestWorld.badGeometryLookup then return original(44) end
                return original(index)
            end
        ''')
        self.assertFalse(self.safe())
        self.w.badGeometryLookup = False
        self.assertTrue(self.safe())

    def test_unavailable_religious_layer_is_not_cached_as_clear_or_threat(self):
        self.lua.execute('''
            local original=Units.GetUnitsInPlotLayerID
            TestWorld.badGeometryReligion=true
            Units.GetUnitsInPlotLayerID=function(plot,layer)
                if plot:GetIndex()==43 and TestWorld.badGeometryReligion then return nil end
                return original(plot,layer)
            end
        ''')
        cache = self.lua.table()
        self.assertFalse(self.safe(cache=cache))
        self.w.badGeometryReligion = False
        self.assertTrue(self.safe(cache=cache))

    def test_radius_change_without_a_binding_change_gets_a_new_footprint(self):
        self.geometry(radius=1)
        before = self.w.geometryCalls
        self.geometry(radius=2)
        self.assertGreater(self.w.geometryCalls, before)

    def test_metadata_contains_only_numeric_identity_and_coordinates(self):
        for cell in self.geometry().values():
            self.assertEqual(set(cell.keys()), {'index', 'x', 'y'})
            self.assertTrue(all(isinstance(value, (int, float)) for value in cell.values()))

    def test_world_ready_discards_geometry_even_with_unchanged_native_bindings(self):
        self.geometry(radius=0)
        before = self.w.geometryCalls
        self.w.geometryWorldReady()
        self.geometry(radius=0)
        self.assertGreater(self.w.geometryCalls, before)
        self.assertEqual(len(self.w.unitRequests), 0)

    def test_shutdown_removes_the_world_ready_listener(self):
        self.assertIsNotNone(self.w.geometryWorldReady)
        self.lua.globals().BaiqiController.Shutdown()
        self.assertIsNone(self.w.geometryWorldReady)


if __name__ == '__main__':
    unittest.main()
