"""Actual Controller GP path phases on both Lua engines; no game process."""
from pathlib import Path
import unittest
from unittest.mock import patch
from lupa.lua51 import LuaRuntime as L51
from lupa.lua53 import LuaRuntime as L53
import test_baiqi_scientist as scientist
ROOT=Path(__file__).resolve().parents[1]
PREFIX="""TestWorld.routeLoadHandlers={}
Events.LoadGameViewStateDone={Add=function(fn)TestWorld.routeLoadHandlers[fn]=true end,Remove=function(fn)TestWorld.routeLoadHandlers[fn]=nil end}
"""
SUFFIX="\nTestDistrictRoutePrivate={Plans=function()return districtPersonPlans end,Run=function(p)return districtRoute.Run(p)end}\n"
class DistrictPersonPathPhaseTests(unittest.TestCase):
 def world(self,Engine):
  f=scientist.BaiqiScientistTests()
  original=Path.read_text;controller=ROOT/'mod/Baiqi/Lua/BaiqiController.lua'
  def probed(path,*args,**kw):
   raw=original(path,*args,**kw)
   return PREFIX+raw+SUFFIX if path.resolve()==controller.resolve()else raw
  with patch.object(scientist,'LuaRuntime',Engine),patch.object(Path,'read_text',probed):f.setUp()
  f.lua.execute('''Automation={GetTime=function()return 100 end}
TestWorld.routeReads=0
local query=UnitManager.GetMoveToPathEx
UnitManager.GetMoveToPathEx=function(...)TestWorld.routeReads=TestWorld.routeReads+1;return query(...)end
''')
  return f
 def moves(self,f):
  self.assertNotIn('脚本错误',f.c.GetStatus())
  return [r for r in f.w.unitRequests.values()if r.op==10]
 def queued(self,f):
  f.c.RunNow();p=f.lua.globals().TestDistrictRoutePrivate.Plans()[4]
  self.assertIsNotNone(p);self.assertIsNotNone(p.route)
  self.assertEqual(p.route.phase,'query');self.assertEqual(f.w.routeReads,0);self.assertEqual(self.moves(f),[])
  return p
 def queried(self,f):
  p=self.queued(f);f.c.RunNow()
  self.assertEqual((p.route.phase,f.w.routeReads),('validate',1));self.assertEqual(self.moves(f),[])
  return p
 def test_query_and_full_validation_use_distinct_callbacks_then_original_writer_once(self):
  for E in(L51,L53):
   f=self.world(E);p=self.queried(f)
   f.c.RunNow();self.assertEqual(self.moves(f),[]) # ordinary scheduling slot.
   f.c.RunNow();self.assertEqual(len(self.moves(f)),1)
   self.assertEqual((self.moves(f)[0].unit,self.moves(f)[0].params[14],self.moves(f)[0].params[15]),(4,3,3))
   self.assertIsNone(p.route);self.assertEqual(f.w.routeReads,1)
   f.c.RunNow();f.c.RunNow();self.assertEqual((len(self.moves(f)),f.w.routeReads),(1,1))
 def test_between_phase_threat_owner_formation_and_metadata_prevent_movement(self):
  changes=['TestWorld.enemy=true','TestWorld.scientistOwner=8','TestWorld.scientistFormation=2',
           'TestWorld.scientistFormation=nil','TestWorld.scientistCharges=0',
           'TestWorld.scientistReady=false','TestWorld.queuedDestination=43',
           'TestWorld.hiddenTarget=true','TestWorld.completed=false',
           'Map.GetPlotByIndex(43).GetOwner=function()return 8 end',
           'TestWorld.scientistCharges=2',
           "GameInfo.GreatPersonIndividuals[71]={Index=71,GreatPersonClassType='GREAT_PERSON_CLASS_SCIENTIST',ActionRequiresCompletedDistrictType='DISTRICT_CAMPUS'};TestWorld.scientistIndividual=71",
           "GameInfo.GreatPersonIndividuals[70].ActionRequiresCompletedDistrictType=nil"]
  for change in changes:
   for E in(L51,L53):
    with self.subTest(change=change,VM=E.__module__):
     f=self.world(E);p=self.queried(f);f.lua.execute(change)
     f.c.RunNow();f.c.RunNow();self.assertEqual(self.moves(f),[])
     self.assertIsNone(p.route)
 def test_native_query_cannot_change_identity_formation_or_charge_and_create_a_write(self):
  for change in ['TestWorld.scientistOwner=8','TestWorld.scientistFormation=2','TestWorld.scientistCharges=0','TestWorld.scientistMoves=1','TestWorld.turn=TestWorld.turn+1']:
   for E in(L51,L53):
    with self.subTest(change=change,VM=E.__module__):
     f=self.world(E);p=self.queued(f)
     f.lua.execute('local original=UnitManager.GetMoveToPathEx;UnitManager.GetMoveToPathEx=function(...)local result=original(...);'+change+';return result end')
     f.c.RunNow();self.assertIsNone(p.route);self.assertEqual(self.moves(f),[])
 def test_end_guard_and_native_busy_prevent_query_resume(self):
  for change in ['TestWorld.busy=true','TestWorld.processing=true','BaiqiController.SetTurnGuard(function()return false end)']:
   for E in(L51,L53):
    f=self.world(E);self.queued(f);f.lua.execute(change);f.c.RunNow()
    self.assertEqual(f.w.routeReads,0);self.assertEqual(self.moves(f),[])
 def test_clock_loss_after_query_does_not_requery_or_repeat_the_write(self):
  for E in(L51,L53):
   f=self.world(E);self.queried(f);f.lua.execute('Automation=nil')
   f.c.RunNow();f.c.RunNow();self.assertEqual((len(self.moves(f)),f.w.routeReads),(1,1))
 def test_native_path_nil_error_holes_and_noninteger_points_do_not_write(self):
  for result in ["return nil","error('path unavailable')","return{plots={[1]=42,[3]=43}}","return{plots={42,43.5}}"]:
   for E in(L51,L53):
    f=self.world(E);p=self.queued(f);f.lua.execute('UnitManager.GetMoveToPathEx=function(...)TestWorld.routeReads=TestWorld.routeReads+1;'+result+' end')
    f.c.RunNow();self.assertIsNone(p.route);self.assertEqual(self.moves(f),[])
 def test_turn_change_invalidates_an_unsent_job(self):
  for E in(L51,L53):
   f=self.world(E);p=self.queried(f)
   f.lua.execute('TestWorld.turn=TestWorld.turn+1')
   f.c.RunNow(False);self.assertIsNone(p.route);self.assertEqual(self.moves(f),[])
 def test_actual_registered_load_handler_discards_the_unsent_job(self):
  for E in(L51,L53):
   f=self.world(E);p=self.queried(f)
   f.lua.execute('for fn in pairs(TestWorld.routeLoadHandlers)do fn()end')
   self.assertIsNone(p.route);self.assertEqual(self.moves(f),[])
   self.assertEqual(f.w.routeReads,1)
 def test_pending_gp_query_leaves_the_next_callback_to_city_planning(self):
  for E in(L51,L53):
   f=self.world(E);self.queried(f)
   f.lua.execute('local city=TestWorld.objects.city;local read=city.GetBuildQueue;TestWorld.routeCityReads=0;city.GetBuildQueue=function(...)TestWorld.routeCityReads=TestWorld.routeCityReads+1;return read(...)end')
   f.c.RefreshProduction();f.c.RunNow()
   self.assertGreater(f.w.routeCityReads,0);self.assertEqual(self.moves(f),[])
   f.c.RunNow();self.assertEqual(len(self.moves(f)),1)
 def test_native_query_binding_change_cannot_authorize_the_cached_result(self):
  for E in(L51,L53):
   f=self.world(E);p=self.queued(f)
   f.lua.execute('local query=UnitManager.GetMoveToPathEx;UnitManager.GetMoveToPathEx=function(...)local path=query(...);UnitManager.GetMoveToPathEx=function()return path end;return path end')
   f.c.RunNow();self.assertIsNone(p.route);self.assertEqual(self.moves(f),[])
 def test_new_held_activation_intent_between_phases_prevents_the_queued_move(self):
  for E in(L51,L53):
   f=self.world(E);p=self.queried(f);f.w.scientistPlot=43
   granted,_,_=f.lua.globals().ExposedMembers.BaiqiGreatPersonIntentBridge.Prepare(7,4,'UNIT_GREAT_SCIENTIST',5,70,1,3,3)
   self.assertTrue(granted);f.w.scientistPlot=42
   f.c.RunNow();f.c.RunNow()
   self.assertIsNone(p.route);self.assertEqual(self.moves(f),[])
   self.assertEqual(len(f.w.commandRequests),0)
 def test_final_native_qualification_cannot_move_a_newly_escorted_or_foreign_actor(self):
  for change in ['TestWorld.scientistFormation=2','TestWorld.scientistOwner=8','TestWorld.busy=true','TestWorld.enemy=true']:
   for E in(L51,L53):
    f=self.world(E);self.queried(f);f.c.RunNow()
    f.lua.execute('local can=UnitManager.CanStartOperation;UnitManager.CanStartOperation=function(u,op,...)local result=can(u,op,...);if op==10 then '+change+' end;return result end')
    f.c.RunNow();self.assertEqual(self.moves(f),[])
