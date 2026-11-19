"""Actual controller safety reads: fresh public plots, threats and unknowns."""
from pathlib import Path
import unittest
from unittest.mock import patch

from lupa.lua51 import LuaRuntime as Lua51
from lupa.lua53 import LuaRuntime as Lua53
from tests import test_baiqi_settlement_border as border

ROOT = Path(__file__).resolve().parents[1]
CONTROLLER = ROOT / 'mod/Baiqi/Lua/BaiqiController.lua'
EXPORT = '''
TestSafe172=Safe;TestSafeGeometry172=NeighborhoodGeometry
function TestSafeContext172(v)visibility=v;contextID=7 end
'''
WORLD = '''
SafeWorld={xyReads=0,indexReads=0,coordinateReads=0,unitReads=0,
 visible=true,revealed=true,enemy=false,religiousEnemy=false,war=true}
local w=SafeWorld
local center={GetIndex=function()return 10 end,GetX=function()return 20 end,GetY=function()return 20 end}
local neighbor={GetIndex=function()w.indexReads=w.indexReads+1;return 11 end,
 GetX=function()w.xyReads=w.xyReads+1;return 21 end,
 GetY=function()w.xyReads=w.xyReads+1;return 20 end}
w.center=center;w.neighbor=neighbor
local coordinates={['20:20']=center,['21:20']=neighbor}
Map.GetPlot=function(x,y)w.coordinateReads=w.coordinateReads+1;return coordinates[x..':'..y]end
Map.GetPlotByIndex=function(i)if i==10 then return center elseif i==11 then return neighbor end end
Map.GetPlotXYWithRangeCheck=function(x,y,dx,dy,r)
 assert(x==20 and y==20 and r==1)
 if dx==0 and dy==0 then return center elseif dx==1 and dy==0 then return neighbor end
end
local visibility={IsRevealed=function(_,x,y)if x==21 then return w.revealed end;return true end,
 IsVisible=function(_,x,y)if x==21 then return w.visible end;return true end}
TestSafeContext172(visibility)
Units.GetUnitsInPlot=function(p)
 w.unitReads=w.unitReads+1
 if p==neighbor and w.enemy then return {{GetOwner=function()return 8 end}} end
 return {}
end
MapLayers={RELIGIOUS=3}
Units.GetUnitsInPlotLayerID=function(p,layer)
 assert(layer==3);w.unitReads=w.unitReads+1
 if p==neighbor and w.religiousEnemy then return {{GetOwner=function()return 8 end}} end
 return {}
end
w.player={GetDiplomacy=function()return {IsAtWarWith=function(_,owner)assert(owner==8);return w.war end}end}
BaiqiConfig.threatRadius=1
assert(TestSafeGeometry172(center,1))
w.xyReads=0;w.indexReads=0;w.coordinateReads=0;w.unitReads=0
'''


class SafeCoordinateLookupTests(unittest.TestCase):
    def world(self, runtime):
        fixture = border.SettlementBorderTests()
        original_read = Path.read_text

        def exported(path, *args, **kwargs):
            text = original_read(path, *args, **kwargs)
            return text + EXPORT if path.resolve() == CONTROLLER else text

        with patch.object(border, 'LuaRuntime', runtime), patch.object(Path, 'read_text', exported):
            fixture.setUp()
        fixture.lua.execute(WORLD)
        return fixture.lua, fixture.lua.globals().SafeWorld

    def safe(self, lua, world):
        result = lua.globals().TestSafe172(world.center, world.player)
        self.assertEqual(len(lua.globals().TestWorld.unitRequests), 0)
        return result

    def test_public_neighbor_removes_only_redundant_coordinate_reads(self):
        for runtime in (Lua51, Lua53):
            with self.subTest(lua=runtime.__module__):
                lua, w = self.world(runtime)
                self.assertIs(self.safe(lua, w), True)
                # Four fresh reads remain in revelation/visibility qualification.
                self.assertEqual((w.xyReads, w.indexReads, w.coordinateReads, w.unitReads), (4, 1, 2, 4))

    def test_index_only_api_keeps_live_coordinate_validation(self):
        for runtime in (Lua51, Lua53):
            lua, w = self.world(runtime)
            lua.execute('Map.GetPlot=nil')
            self.assertIs(self.safe(lua, w), True)
            self.assertEqual((w.xyReads, w.indexReads, w.coordinateReads), (6, 1, 0))
            lua.execute('SafeWorld.neighbor.GetX=function()return 22 end')
            self.assertIs(self.safe(lua, w), False)

    def test_hidden_neighbor_never_resolves_or_reads_its_units(self):
        for runtime in (Lua51, Lua53):
            lua, w = self.world(runtime)
            w.visible, w.enemy = False, True
            self.assertIs(self.safe(lua, w), True)
            self.assertEqual((w.xyReads, w.indexReads, w.coordinateReads, w.unitReads), (0, 0, 1, 2))
            w.visible = True
            self.assertIs(self.safe(lua, w), False)

    def test_unknown_visibility_never_means_no_threat(self):
        for runtime in (Lua51, Lua53):
            for value in (None, 0, 'false'):
                with self.subTest(lua=runtime.__module__, value=value):
                    lua, w = self.world(runtime)
                    w.visible = value
                    self.assertIs(self.safe(lua, w), False)
                    self.assertEqual(w.xyReads, 0)

    def test_throwing_visibility_holds_without_stopping_controller(self):
        for runtime in (Lua51, Lua53):
            lua, w = self.world(runtime)
            lua.execute("TestSafeContext172({IsRevealed=function()return true end,IsVisible=function()error('unknown visibility')end})")
            self.assertIs(self.safe(lua, w), False)
            self.assertEqual((w.coordinateReads, w.unitReads), (0, 0))

    def test_ground_and_religious_threats_are_fresh(self):
        for runtime in (Lua51, Lua53):
            for field in ('enemy', 'religiousEnemy'):
                with self.subTest(lua=runtime.__module__, field=field):
                    lua, w = self.world(runtime)
                    self.assertIs(self.safe(lua, w), True)
                    setattr(w, field, True)
                    self.assertIs(self.safe(lua, w), False)
                    w.war = False
                    self.assertIs(self.safe(lua, w), True)

    def test_bad_coordinate_results_hold_without_index_fallback(self):
        for runtime in (Lua51, Lua53):
            for result in ('return nil', "error('unknown coordinate')", 'return SafeWorld.center'):
                with self.subTest(lua=runtime.__module__, result=result):
                    lua, w = self.world(runtime)
                    lua.execute('local original=Map.GetPlot;Map.GetPlot=function(x,y)if x==21 then '
                                + result + ' end;return original(x,y)end')
                    self.assertIs(self.safe(lua, w), False)

    def test_lookup_binding_change_cannot_leave_positive_permission(self):
        for runtime in (Lua51, Lua53):
            for name in ('GetPlot', 'GetPlotByIndex'):
                with self.subTest(lua=runtime.__module__, name=name):
                    lua, w = self.world(runtime)
                    lua.execute('local original=Map.GetPlot;Map.GetPlot=function(x,y)'
                                'if x==21 then Map.' + name + '=function()return nil end end;return original(x,y)end')
                    self.assertIs(self.safe(lua, w), False)

    def test_missing_religious_layer_does_not_authorize_a_safe_path(self):
        for runtime in (Lua51, Lua53):
            lua, w = self.world(runtime)
            lua.execute('Units.GetUnitsInPlotLayerID=nil')
            self.assertIs(self.safe(lua, w), False)


if __name__ == '__main__':
    unittest.main()
