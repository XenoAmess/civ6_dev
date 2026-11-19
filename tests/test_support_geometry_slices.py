"""Bounded immutable support geometry with fresh permission checks; actual Controller."""
from pathlib import Path
import unittest
from unittest.mock import patch
from lupa.lua51 import LuaRuntime as L51
from lupa.lua53 import LuaRuntime as L53
from tests import test_baiqi_settlement_border as border
ROOT=Path(__file__).resolve().parents[1]
target=ROOT/'mod/Baiqi/Lua/BaiqiController.lua'
PREFIX='TestWorld.geoLoads={};Events.LoadGameViewStateDone={Add=function(fn)TestWorld.geoLoads[fn]=true end,Remove=function(fn)TestWorld.geoLoads[fn]=nil end}\n'
EXPORT='\nTestSupport167={Geometry=NeighborhoodGeometry,Support=KnownExpansionSupport,Jobs=function()return neighborhoodJobs end,Targets=function()return settlementTargets end}\n'
class SupportGeometryTests(unittest.TestCase):
 def world(self,E,clock=True):
  f=border.SettlementBorderTests();outer=Path.read_text
  def hooked(path,*args,**kwargs):
   text=outer(path,*args,**kwargs);return PREFIX+text+EXPORT if path.resolve()==target else text
  with patch.object(border,'LuaRuntime',E),patch.object(Path,'read_text',hooked):f.setUp()
  f.w.foreign=False
  if clock:f.lua.execute('Automation={GetTime=function()return 100 end}')
  f.controller.RunNow(False)
  f.lua.execute('''TestWorld.geometryCalls={};local old=Map.GetPlotXYWithRangeCheck
Map.GetPlotXYWithRangeCheck=function(x,y,dx,dy,r)TestWorld.geometryCalls[r]=(TestWorld.geometryCalls[r]or 0)+1;return old(x,y,dx,dy,r)end''')
  return f
 def calls(self,f):return f.w.geometryCalls[9]or 0
 def geometry(self,f,slice=24):return f.lua.globals().TestSupport167.Geometry(f.lua.globals().Map.GetPlotByIndex(47),9,slice)
 def result(self,v):return v[0]if isinstance(v,tuple)else v
 def moves(self,f):return[r for r in f.w.unitRequests.values()if r.op==10]
 def step(self,f):
  before=self.calls(f);f.controller.RunNow();self.assertLessEqual(self.calls(f)-before,24);self.assertNotIn('脚本错误',f.controller.GetStatus())
 def until_move(self,f,limit=80):
  before=len(self.moves(f))
  for _ in range(limit):
   self.step(f)
   if len(self.moves(f))>before:return
  self.fail('Qualified pending geometry never resumed movement')
 def test_geometry_each_slice_is_bounded_and_complete_list_matches_sync(self):
  for E in(L51,L53):
   f=self.world(E);result=None;calls=0
   for _ in range(20):
    before=self.calls(f);v=self.geometry(f);calls+=1;self.assertLessEqual(self.calls(f)-before,24)
    if self.result(v)is not None:result=self.result(v);break
    self.assertTrue(v[2])
   self.assertIsNotNone(result);self.assertEqual((calls,self.calls(f)),(16,361))
   a=[(v.index,v.x,v.y)for v in result.values()];g=self.world(E)
   b=[(v.index,v.x,v.y)for v in self.result(self.geometry(g,None)).values()];self.assertEqual(a,b)
 def test_full_controller_cold_search_waits_then_moves_without_repeating_whole_geometry(self):
  for E in(L51,L53):
   f=self.world(E);self.step(f);self.assertEqual(self.moves(f),[])
   self.until_move(f);self.assertEqual(len(self.moves(f)),1);self.assertEqual(self.calls(f),361)
 def test_existing_goal_is_retained_during_topology_wait(self):
  for E in(L51,L53):
   f=self.world(E);self.until_move(f);self.assertEqual(f.lua.globals().TestSupport167.Targets()[2],47)
   f.w.turn+=1;f.w.settlerPlot=43;f.lua.execute('for fn in pairs(TestWorld.geoLoads)do fn()end')
   before=len(self.moves(f));self.step(f)
   self.assertEqual(f.lua.globals().TestSupport167.Targets()[2],47);self.assertEqual(len(self.moves(f)),before)
 def test_new_foreign_city_before_geometry_completion_refuses_movement(self):
  for E in(L51,L53):
   f=self.world(E)
   for _ in range(4):self.step(f)
   f.w.foreign=True
   for _ in range(40):self.step(f)
   self.assertEqual(self.moves(f),[]);self.assertEqual([r for r in f.w.unitRequests.values()if r.op==11],[])
 def test_owner_formation_and_hidden_goal_changes_do_not_authorize_any_move(self):
  for change in('TestWorld.objects.settler.GetOwner=function()return 8 end','TestWorld.objects.settler.GetFormationUnitCount=function()return 2 end','TestWorld.hidden[47]=true'):
   for E in(L51,L53):
    f=self.world(E);self.step(f);f.lua.execute(change)
    for _ in range(30):self.step(f)
    self.assertEqual(self.moves(f),[]);self.assertEqual([r for r in f.w.unitRequests.values()if r.op==11],[])
 def test_actual_registered_load_discards_partial_scalar_job(self):
  for E in(L51,L53):
   f=self.world(E);self.geometry(f);self.assertEqual(len(list(f.lua.globals().TestSupport167.Jobs().values())),1)
   f.lua.execute('for fn in pairs(TestWorld.geoLoads)do fn()end');self.assertEqual(list(f.lua.globals().TestSupport167.Jobs().values()),[])
   before=self.calls(f);v=self.geometry(f);self.assertIsNone(v[0]);self.assertTrue(v[2]);self.assertEqual(self.calls(f)-before,24)
 def test_clock_loss_during_partial_job_uses_original_sync_fallback(self):
  for E in(L51,L53):
   f=self.world(E);self.step(f);before=self.calls(f);self.assertEqual(self.moves(f),[])
   f.lua.execute('Automation=nil');f.controller.RunNow()
   self.assertEqual(len(self.moves(f)),1);self.assertEqual(self.calls(f)-before,361);self.assertNotIn('脚本错误',f.controller.GetStatus())
 def test_native_binding_change_restarts_partial_geometry_without_permission(self):
  for E in(L51,L53):
   f=self.world(E);self.geometry(f);old=list(f.lua.globals().TestSupport167.Jobs().values())[0];self.assertGreater(old.dy,-9)
   f.lua.execute('local old=Map.GetPlotByIndex;Map.GetPlotByIndex=function(...)return old(...)end')
   before=self.calls(f);v=self.geometry(f);current=list(f.lua.globals().TestSupport167.Jobs().values())[0]
   self.assertIsNone(v[0]);self.assertTrue(v[2]);self.assertEqual(self.calls(f)-before,24);self.assertEqual((current.dx,current.dy),(old.dx,old.dy));self.assertEqual(self.moves(f),[])
 def test_missing_native_anchor_rejects_geometry_and_never_makes_it_ready(self):
  for E in(L51,L53):
   f=self.world(E)
   f.lua.execute('local old=Map.GetPlotXYWithRangeCheck;Map.GetPlotXYWithRangeCheck=function(x,y,dx,dy,r)if r==9 and dx==0 and dy==0 then return nil end;return old(x,y,dx,dy,r)end')
   last=None
   for _ in range(20):
    v=self.geometry(f);last=v
    if not isinstance(v,tuple)or len(v)<3 or not v[2]:break
   self.assertIsNone(self.result(last));self.assertEqual(list(f.lua.globals().TestSupport167.Jobs().values()),[]);self.assertEqual(self.moves(f),[])
 def test_final_found_qualification_rechecks_new_foreign_city_after_geometry_ready(self):
  for E in(L51,L53):
   f=self.world(E);f.w.settlerPlot=47
   f.lua.execute('TestWorld.foundGateReads=0;local old=UnitManager.CanStartOperation;UnitManager.CanStartOperation=function(u,op,...)local v=old(u,op,...);if op==11 then TestWorld.foundGateReads=TestWorld.foundGateReads+1;TestWorld.foreign=true end;return v end')
   for _ in range(50):self.step(f)
   self.assertGreater(f.w.foundGateReads,0);self.assertEqual([r for r in f.w.unitRequests.values()if r.op==11],[]);self.assertEqual(self.moves(f),[])
