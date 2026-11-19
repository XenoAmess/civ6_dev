"""Fresh known-border visibility avoids unused hidden plot reads; actual controller."""
from pathlib import Path
import unittest
from unittest.mock import patch
from lupa.lua51 import LuaRuntime as L51
from lupa.lua53 import LuaRuntime as L53
from tests import test_baiqi_settlement_border as border
ROOT=Path(__file__).resolve().parents[1]
class SupportPublicCellsTests(unittest.TestCase):
 def world(self,Engine):
  f=border.SettlementBorderTests()
  read=Path.read_text;target=ROOT/'mod/Baiqi/Lua/BaiqiController.lua'
  def exported(path,*a,**k):
   text=read(path,*a,**k)
   return text+'\nTestKnownSupport165=KnownExpansionSupport\n'if path.resolve()==target else text
  with patch.object(border,'LuaRuntime',Engine),patch.object(Path,'read_text',exported):f.setUp()
  f.controller.RunNow(False)
  f.lua.execute('''local original=Map.GetPlotByIndex;TestWorld.foreignPlotReads=0
Map.GetPlotByIndex=function(index)
 if index==200 then TestWorld.foreignPlotReads=TestWorld.foreignPlotReads+1 end
 return original(index)
end''')
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
