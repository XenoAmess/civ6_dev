"""Actual Controller short-leg routing; both Lua VMs, no native game process."""
from pathlib import Path
import unittest
from unittest.mock import patch
from lupa.lua51 import LuaRuntime as L51
from lupa.lua53 import LuaRuntime as L53
from tests import test_baiqi_scientist as scientist
ROOT=Path(__file__).resolve().parents[1]
_read=Path.read_text
def instrumented(path,*args,**kwargs):
 text=_read(path,*args,**kwargs)
 return PREFIX+text+SUFFIX if path.resolve()==ROOT/'mod/Baiqi/Lua/BaiqiController.lua'else text
PREFIX='TestWorld.shortLoad=TestWorld.routeLoadHandlers or {};Events.LoadGameViewStateDone={Add=function(fn)TestWorld.shortLoad[fn]=true end,Remove=function(fn)TestWorld.shortLoad[fn]=nil end}\n'
SUFFIX='\nTestShortRoutePlans=function()return districtPersonPlans end\n'
WORLD="\nlocal w=TestWorld;local o=w.objects\nAutomation={GetTime=function()return 100 end}\nw.shortXY={[42]={0,0},[44]={1,0},[45]={0,1},[46]={1,1},[47]={2,1},[43]={3,0}}\nw.shortEdges={[42]={44,45},[44]={42},[45]={42,46},[46]={45,47},[47]={46,43},[43]={47}}\nw.shortPlots={};w.rangeReads=0;w.pathReads=0;w.shortQueries={};w.shortPublic={}\nfor index,xy in pairs(w.shortXY)do\n local id,x,y=index,xy[1],xy[2]\n w.shortPlots[index]={GetIndex=function()return id end,GetX=function()return x end,GetY=function()return y end,\n GetOwner=function()return w.shortForeign==id and 8 or 7 end,IsImpassable=function()return false end}\nend\nMap.GetPlotByIndex=function(id)return w.shortPlots[id]end\nMap.GetPlot=function(x,y)for _,p in pairs(w.shortPlots)do if p:GetX()==x and p:GetY()==y then return p end end end\nMap.GetPlotDistance=function(x,y,tx,ty)local dx,dy=x-tx,y-ty;return math.max(math.abs(dx),math.abs(dy),math.abs(dx+dy))end\nMap.GetPlotXYWithRangeCheck=function(x,y,dx,dy)if dx==0 and dy==0 then return Map.GetPlot(x,y)end end\nMap.GetAdjacentPlot=function(x,y,dir)local p=Map.GetPlot(x,y);local edges=p and w.shortEdges[p:GetIndex()];return edges and w.shortPlots[edges[dir+1]]end\nPlayersVisibility[7].IsRevealed=function(_,x,y)local p=Map.GetPlot(x,y);return p and not w.shortHidden or false end\nPlayersVisibility[7].IsVisible=function()return true end\nUnits.GetUnitsInPlot=function(p)if p:GetIndex()==w.shortEnemy then return{{GetOwner=function()return 8 end}}end;return{}end\nlocal u=o.player:GetUnits():FindID(4)\nu.GetX=function()return w.shortPlots[w.scientistPlot]:GetX()end\nu.GetY=function()return w.shortPlots[w.scientistPlot]:GetY()end\nu.HasMovedIntoZOC=function()return w.shortZoc or false end\no.city.GetDistricts=function()\n return{HasDistrict=function()return w.completed end,Members=function()local done=false;return function()if not done then done=true;return 1,{GetType=function()return 7 end,GetX=function()return 3 end,GetY=function()return 0 end}end end end}\nend\nUnitManager.GetReachableMovement=function(unit)\n assert(unit:GetID()==4,'Military reached movement-range query');w.rangeReads=w.rangeReads+1\n local result={w.scientistPlot};for _,id in ipairs(w.shortEdges[w.scientistPlot]or{})do result[#result+1]=id end\n return result\nend\nUnitManager.GetMoveToPathEx=function(unit,index)\n assert(unit:GetID()==4,'Military reached path query');w.pathReads=w.pathReads+1\n local a=w.shortPlots[w.scientistPlot];local b=w.shortPlots[index]\n assert(b and Map.GetPlotDistance(a:GetX(),a:GetY(),b:GetX(),b:GetY())==1,'Unbounded remote goal query')\n w.shortQueries[#w.shortQueries+1]=index\n return{plots={w.scientistPlot,index}}\nend\nfunction w.ApplyShortMove()\n local row=w.unitRequests[#w.unitRequests];if not row or row.op~=10 then return false end\n local p=Map.GetPlot(row.params[14],row.params[15]);assert(p)\n w.scientistPlot=p:GetIndex();w.scientistMoves=2;w.turn=w.turn+1\n return true\nend\n"
class ShortLegRouteTests(unittest.TestCase):
 def world(self,E):
  f=scientist.BaiqiScientistTests()
  with patch.object(scientist,'LuaRuntime',E),patch.object(Path,'read_text',instrumented):f.setUp()
  f.lua.execute(WORLD);return f
 def moves(self,f):return [r for r in f.w.unitRequests.values()if r.op==10]
 def step(self,f):
  before=f.w.rangeReads+f.w.pathReads;f.c.RunNow();self.assertLessEqual(f.w.rangeReads+f.w.pathReads-before,1)
  self.assertNotIn('脚本错误',f.c.GetStatus())
 def until_move(self,f,limit=20):
  before=len(self.moves(f))
  for _ in range(limit):
   self.step(f)
   if len(self.moves(f))>before:return self.moves(f)[-1]
  self.fail('No qualified short-leg move')
 def test_range_query_and_validation_are_separate_and_remote_goal_never_queried(self):
  for E in(L51,L53):
   f=self.world(E);self.step(f);self.assertEqual((f.w.rangeReads,f.w.pathReads,len(self.moves(f))),(0,0,0))
   self.step(f);self.assertEqual((f.w.rangeReads,f.w.pathReads,len(self.moves(f))),(1,0,0))
   row=self.until_move(f);self.assertEqual((row.params[14],row.params[15]),(1,0));self.assertEqual(f.w.pathReads,1)
   self.assertNotIn(43,list(f.w.shortQueries.values()))
 def test_dead_end_backtracks_and_reaches_original_district_then_activates(self):
  for E in(L51,L53):
   f=self.world(E);positions=[]
   for _ in range(12):
    self.until_move(f);self.assertTrue(f.w.ApplyShortMove());positions.append(f.w.scientistPlot)
    if f.w.scientistPlot==43:break
   self.assertEqual(positions,[44,42,45,46,47,43])
   for _ in range(5):self.step(f)
   self.assertEqual(len(f.w.commandRequests),1)
 def test_malformed_range_does_not_fall_back_to_remote_native_path(self):
  for value in ('nil','false','{[1]=42,[3]=44}','{42,44.5}',"{[1]=42,extra=44}"):
   for E in(L51,L53):
    f=self.world(E);f.lua.execute('UnitManager.GetReachableMovement=function()TestWorld.rangeReads=TestWorld.rangeReads+1;return '+value+' end')
    for _ in range(8):self.step(f)
    self.assertEqual((f.w.pathReads,len(self.moves(f))),(0,0))
 def test_range_call_cannot_change_owner_formation_charge_or_binding_and_authorize_move(self):
  for change in ('TestWorld.scientistOwner=8','TestWorld.scientistFormation=2','TestWorld.scientistCharges=0','UnitManager.GetReachableMovement=function()return {42,44}end'):
   for E in(L51,L53):
    f=self.world(E);self.step(f)
    f.lua.execute('local old=UnitManager.GetReachableMovement;UnitManager.GetReachableMovement=function(...)local r=old(...);'+change+';return r end')
    self.step(f);self.assertEqual((f.w.pathReads,len(self.moves(f))),(0,0))
 def test_escorted_foreign_and_zoc_actor_never_receive_range_or_path_query(self):
  for change in ('TestWorld.scientistFormation=2','TestWorld.scientistOwner=8','TestWorld.shortZoc=true'):
   for E in(L51,L53):
    f=self.world(E);f.lua.execute(change)
    for _ in range(8):self.step(f)
    self.assertEqual((f.w.rangeReads,f.w.pathReads,len(self.moves(f))),(0,0,0))
 def test_threat_after_query_rejects_leg_before_original_writer(self):
  for E in(L51,L53):
   f=self.world(E)
   while f.w.pathReads==0:self.step(f)
   f.w.shortEnemy=44
   for _ in range(2):self.step(f)
   self.assertEqual(len(self.moves(f)),0)
 def test_held_intent_during_range_never_queries_or_moves(self):
  for E in(L51,L53):
   f=self.world(E);self.step(f)
   granted,_,_=f.lua.globals().ExposedMembers.BaiqiGreatPersonIntentBridge.Prepare(7,4,'UNIT_GREAT_SCIENTIST',5,70,1,0,0)
   self.assertTrue(granted);self.step(f);self.assertEqual((f.w.rangeReads,f.w.pathReads,len(self.moves(f))),(0,0,0))
 def test_actual_load_handler_clears_walk_proposals_and_unsent_route(self):
  for E in(L51,L53):
   f=self.world(E);self.step(f);self.step(f);plan=f.lua.globals().TestShortRoutePlans()[4]
   self.assertIsNotNone(plan.walk);f.lua.execute('for fn in pairs(TestWorld.shortLoad)do fn()end')
   self.assertIsNone(plan.walk);self.assertIsNone(plan.route);self.assertEqual(len(self.moves(f)),0)
 def test_goal_activation_precedes_any_range_search(self):
  for E in(L51,L53):
   f=self.world(E);f.w.scientistPlot=43;self.step(f)
   self.assertEqual((f.w.rangeReads,f.w.pathReads,len(f.w.commandRequests)),(0,0,1))
 def test_rejected_first_leg_can_use_a_freshly_validated_alternative(self):
  for E in(L51,L53):
   f=self.world(E);f.w.shortEnemy=44
   row=self.until_move(f)
   self.assertEqual((row.params[14],row.params[15]),(0,1))
   self.assertEqual(list(f.w.shortQueries.values()),[44,45])
 def test_foreign_original_goal_after_range_prevents_all_path_queries(self):
  for E in(L51,L53):
   f=self.world(E);self.step(f);self.step(f);f.w.shortForeign=43
   for _ in range(6):self.step(f)
   self.assertEqual((f.w.pathReads,len(self.moves(f))),(0,0))
 def test_range_oversize_and_short_paths_with_foreign_interiors_never_move(self):
  for E in(L51,L53):
   f=self.world(E)
   f.lua.execute('UnitManager.GetReachableMovement=function()TestWorld.rangeReads=TestWorld.rangeReads+1;local r={};for i=1,4097 do r[i]=42 end;return r end')
   for _ in range(8):self.step(f)
   self.assertEqual((f.w.pathReads,len(self.moves(f))),(0,0))
   f=self.world(E);f.w.shortForeign=46
   f.lua.execute('UnitManager.GetMoveToPathEx=function(u,index)TestWorld.pathReads=TestWorld.pathReads+1;return{plots={42,45,46,45,index}}end')
   for _ in range(18):self.step(f)
   self.assertGreater(f.w.pathReads,0);self.assertEqual(len(self.moves(f)),0)
