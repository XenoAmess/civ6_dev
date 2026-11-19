"""Fresh known-border visibility avoids unused hidden plot reads; actual controller."""
from pathlib import Path
import unittest
from unittest.mock import patch
from lupa.lua51 import LuaRuntime as L51
from lupa.lua53 import LuaRuntime as L53
from tests import test_baiqi_settlement_border as border
ROOT=Path(__file__).resolve().parents[1]
class SupportPublicCellsTests(unittest.TestCase):
 def world(self,Engine,warm=True):
  f=border.SettlementBorderTests()
  read=Path.read_text;target=ROOT/'mod/Baiqi/Lua/BaiqiController.lua'
  def exported(path,*a,**k):
   text=read(path,*a,**k)
   return text+'\nTestKnownSupport165=KnownExpansionSupport;TestSupportGeometry171=NeighborhoodGeometry\n'if path.resolve()==target else text
  with patch.object(border,'LuaRuntime',Engine),patch.object(Path,'read_text',exported):f.setUp()
  f.controller.RunNow(False)
  # Independent native visibility oracle: a bad coordinate resolver must not
  # also make that same live cell invisible inside the test double.
  f.lua.execute("local indices={};local target=Map.GetPlotByIndex(47);for dx=-9,9 do for dy=-9,9 do local p=Map.GetPlotXYWithRangeCheck(target:GetX(),target:GetY(),dx,dy,9);if p then indices[p:GetX()..':'..p:GetY()]=p:GetIndex()end end end;PlayersVisibility[7].IsRevealed=function(_,x,y)local i=indices[x..':'..y];return i~=nil and not TestWorld.hidden[i]end;PlayersVisibility[7].IsVisible=function(_,x,y)local i=indices[x..':'..y];return i~=nil and not TestWorld.hidden[i]and not TestWorld.fogged[i]end")
  f.lua.execute("local original=Map.GetPlotByIndex;TestWorld.foreignPlotReads=0;Map.GetPlotByIndex=function(index)if index==200 then TestWorld.foreignPlotReads=TestWorld.foreignPlotReads+1 end;return original(index)end")
  if warm:f.lua.execute('for radius=1,9 do assert(TestSupportGeometry171(Map.GetPlotByIndex(47),radius))end')
  # Topology may query coordinates while cold, but it never reads city flags.
  # Warm tests count only live public-cell coordinate/index lookup consumers.
  f.lua.execute("local coordinate,byIndex=Map.GetPlot,Map.GetPlotByIndex;Map.GetPlot=function(x,y)if x==12 and y==4 then TestWorld.foreignPlotReads=TestWorld.foreignPlotReads+1;if TestWorld.badNeighbor then return byIndex(201)end end;return coordinate(x,y)end;TestWorld.foreignPlotReads=0")
  return f
 def support(self,f):
  v=f.lua.globals().TestKnownSupport165(f.lua.globals().Map.GetPlotByIndex(47),f.w.objects.player,7)
  self.assertNotIn('脚本错误',f.controller.GetStatus());self.assertEqual(len(f.w.unitRequests),0)
  return v[0]if isinstance(v,tuple)else v
 def test_unrevealed_cell_never_resolves_a_live_foreign_plot(self):
  for E in(L51,L53):
   f=self.world(E);f.w.hidden[200]=True
   self.assertTrue(self.support(f));self.assertEqual((f.w.foreignPlotReads,f.w.cityQueries),(0,0))
 def test_fogged_cell_never_resolves_a_live_foreign_plot(self):
  for E in(L51,L53):
   f=self.world(E);f.w.fogged[200]=True
   self.assertTrue(self.support(f));self.assertEqual((f.w.foreignPlotReads,f.w.cityQueries),(0,0))
 def test_warm_geometry_rechecks_visibility_and_newly_public_foreign_city(self):
  for E in(L51,L53):
   f=self.world(E);f.w.hidden[200]=True
   self.assertTrue(self.support(f));f.w.hidden[200]=False
   self.assertFalse(self.support(f));self.assertGreater(f.w.foreignPlotReads,0);self.assertGreater(f.w.cityQueries,0)
 def test_unknown_visibility_and_revelation_remain_unknown(self):
  for method in('IsVisible','IsRevealed'):
   for E in(L51,L53):
    f=self.world(E);f.lua.execute('local old=PlayersVisibility[7].'+method+';PlayersVisibility[7].'+method+"=function(self,x,y)if x==12 and y==4 then return nil end;return old(self,x,y)end")
    self.assertIsNone(self.support(f));self.assertEqual(f.w.foreignPlotReads,0)
 def test_visible_wrong_plot_missing_city_and_unknown_city_flag_reject(self):
  for field in('badNeighbor','lookupMissing','lookupThrows','unknownCityFlag','wrongCityCoordinates','badCityID'):
   for E in(L51,L53):
    with self.subTest(field=field,VM=E.__module__):
     f=self.world(E)
     if field=='unknownCityFlag':f.lua.execute('Map.GetPlotByIndex(201).IsCity=function()return false end')
     f.w[field]=True;self.assertIsNone(self.support(f));self.assertGreater(f.w.foreignPlotReads,0)
 def test_own_city_support_is_fresh_even_when_foreign_cell_stays_hidden(self):
  for E in(L51,L53):
   f=self.world(E);f.w.hidden[200]=True;self.assertTrue(self.support(f))
   f.w.ownX,f.w.ownY=8,4;self.assertFalse(self.support(f));self.assertEqual(f.w.foreignPlotReads,0)


 def test_coordinate_lookup_missing_throw_and_wrong_index_are_unknown(self):
  changes=("return nil","error('coordinate_unavailable')","return Map.GetPlotByIndex(201)")
  for change in changes:
   for E in(L51,L53):
    f=self.world(E);f.w.foreign=False
    f.lua.execute("local old=Map.GetPlot;Map.GetPlot=function(x,y)if x==12 and y==4 then "+change+" end;return old(x,y)end")
    self.assertIsNone(self.support(f))
 def test_coordinate_binding_change_during_positive_scan_is_unknown(self):
  for E in(L51,L53):
   f=self.world(E);f.w.foreign=False
   f.lua.execute('local original=Map.GetPlot;Map.GetPlot=function(x,y)Map.GetPlot=original;return original(x,y)end')
   self.assertIsNone(self.support(f))
 def test_empty_public_cell_uses_coordinate_lookup_and_fresh_index(self):
  for E in(L51,L53):
   f=self.world(E);f.w.foreign=False
   f.lua.execute("local cells=assert(TestSupportGeometry171(Map.GetPlotByIndex(47),9));local mapping={};for _,c in ipairs(cells)do mapping[c.x..':'..c.y]=assert(Map.GetPlotByIndex(c.index))end;TestWorld.emptyCoordinateQueries=0;Map.GetPlot=function(x,y)if x==12 and y==4 then TestWorld.emptyCoordinateQueries=TestWorld.emptyCoordinateQueries+1 end;return mapping[x..':'..y]end;local p=Map.GetPlotByIndex(200);local gx,gy=p.GetX,p.GetY;TestWorld.emptyXYReads=0;p.GetX=function(self)TestWorld.emptyXYReads=TestWorld.emptyXYReads+1;return gx(self)end;p.GetY=function(self)TestWorld.emptyXYReads=TestWorld.emptyXYReads+1;return gy(self)end")
   self.assertTrue(self.support(f));self.assertEqual((f.w.emptyCoordinateQueries,f.w.emptyXYReads),(1,0))
 def test_cold_topology_hidden_or_fogged_city_information_is_not_read(self):
  for field in('hidden','fogged'):
   for E in(L51,L53):
    f=self.world(E,warm=False);getattr(f.w,field)[200]=True
    self.assertTrue(self.support(f));self.assertEqual(f.w.cityQueries,0)
