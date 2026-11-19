"""Real Controller phase boundaries; scalar paths do not grant native orders."""
from pathlib import Path
from unittest.mock import patch
import unittest
from lupa.lua51 import LuaRuntime as L51
from lupa.lua53 import LuaRuntime as L53
from tests import test_baiqi_settlement_border as border
from tests import test_baiqi_found_city_receipt as receipt
ROOT=Path(__file__).resolve().parents[1]
C=ROOT/'mod/Baiqi/Lua/BaiqiController.lua';SOURCE=C;READ=Path.read_text
PREFIX='Test169Loads={};Events.LoadGameViewStateDone={Add=function(fn)Test169Loads[fn]=true end,Remove=function(fn)Test169Loads[fn]=nil end};print=function()end\n'
EXPORT='\nTest169={Searches=function()return settlerSearches end,Pending=function()return pendingUnits end,Geometry=NeighborhoodGeometry}\nlocal original=KnownExpansionSupport\nKnownExpansionSupport=function(...)TestWorld.supportCalls=(TestWorld.supportCalls or 0)+1;return original(...)end\n'
def source(path,*a,**k):return PREFIX+READ(SOURCE,encoding='utf-8')+EXPORT if path.resolve()==C else READ(path,*a,**k)

class Settler169Tests(unittest.TestCase):
 def world(self,E=L53,found=False):
  module=receipt if found else border;f=receipt.FoundCityReceiptTests()if found else border.SettlementBorderTests()
  with patch.object(module,'LuaRuntime',E),patch.object(Path,'read_text',source):f.setUp()
  f.w.foreign=False
  f.lua.execute('Automation={GetTime=function()return 100 end};TestWorld.queryCalls=0;local query=UnitManager.GetMoveToPathEx;UnitManager.GetMoveToPathEx=function(...)TestWorld.queryCalls=TestWorld.queryCalls+1;return query(...)end')
  f.c=f.controller;f.a=f.lua.globals().Test169
  f.c.RunNow(False)
  if not found:
   for i in(42,43,44,46,47):
    for radius in range(1,10):f.a.Geometry(f.lua.globals().Map.GetPlotByIndex(i),radius)
  return f
 def step(self,f):
  f.w.queryCalls,f.w.supportCalls=0,0;f.c.RunNow();self.assertNotIn('脚本错误',f.c.GetStatus())
 def moves(self,f):return[r for r in f.w.unitRequests.values()if r.op==10]
 def route(self,f):
  s=f.a.Searches()[2];return s.route if s else None
 def to_phase(self,f,phase):
  for _ in range(60):
   r=self.route(f)
   if r and r.phase==phase:return
   self.step(f)
  self.fail('Missing route phase '+phase)
 def arm(self,f):
  self.step(f);self.assertEqual(f.found_count(),0)
  self.step(f);self.assertEqual(f.found_count(),0)
  self.assertEqual(f.w.settlementBank.operations['2'].stage,'ARMED')

 def test_query_and_final_support_are_separate_callbacks_then_one_move(self):
  for E in(L51,L53):
   f=self.world(E);self.to_phase(f,'query');self.assertEqual(self.moves(f),[])
   self.step(f);self.assertEqual((f.w.queryCalls,f.w.supportCalls),(1,0));self.assertEqual(self.route(f).phase,'write');self.assertEqual(self.moves(f),[])
   self.step(f);self.assertEqual((f.w.queryCalls,len(self.moves(f))),(0,1));self.assertGreaterEqual(f.w.supportCalls,1)

 def test_foreign_city_appearing_after_query_is_not_cached_as_support(self):
  for E in(L51,L53):
   f=self.world(E);self.to_phase(f,'write');f.w.foreign=True
   for _ in range(10):self.step(f)
   self.assertEqual(self.moves(f),[])

 def test_owner_formation_hidden_goal_and_changed_path_refuse_proposal(self):
  cases=('TestWorld.objects.settler.GetOwner=function()return 8 end',
   'TestWorld.objects.settler.GetFormationUnitCount=function()return 2 end',
   'TestWorld.objects.settler.GetFormationUnitCount=function()return nil end',
   'TestWorld.hidden[47]=true','Map.GetPlotByIndex(44).GetOwner=function()return 8 end')
  for E in(L51,L53):
   for change in cases:
    with self.subTest(E=E.__module__,change=change):
     f=self.world(E);self.to_phase(f,'write');f.lua.execute(change)
     for _ in range(8):self.step(f)
     self.assertEqual(self.moves(f),[])

 def test_move_native_qualification_rechecks_formation(self):
  for E in(L51,L53):
   f=self.world(E);self.to_phase(f,'write')
   f.lua.execute('local can=UnitManager.CanStartOperation;UnitManager.CanStartOperation=function(u,op,...)local v=can(u,op,...);if op==10 then TestWorld.objects.settler.GetFormationUnitCount=function()return 2 end end;return v end')
   self.step(f);self.assertEqual(self.moves(f),[])

 def test_clock_loss_restores_original_synchronous_route(self):
  for E in(L51,L53):
   f=self.world(E);self.to_phase(f,'query');f.lua.execute('Automation=nil');self.step(f)
   self.assertEqual((f.w.queryCalls,len(self.moves(f))),(1,1))

 def test_actual_load_event_invalidates_saved_path_proposal(self):
  for E in(L51,L53):
   f=self.world(E);self.to_phase(f,'write');f.lua.execute('for fn in pairs(Test169Loads)do fn()end')
   self.step(f);self.assertEqual(self.moves(f),[])

 def test_malformed_native_path_proposals_do_not_reach_writer(self):
  for E in(L51,L53):
   for bad in ('{plots={[1]=42,[3]=47}}','{plots={42,44,47,extra=9}}','{plots={42,0/0,47}}','{plots={42,"44",47}}'):
    f=self.world(E);self.to_phase(f,'query');f.lua.execute('UnitManager.GetMoveToPathEx=function()return '+bad+' end')
    for _ in range(8):self.step(f)
    self.assertEqual(self.moves(f),[])

 def test_found_proposal_commit_and_native_write_use_distinct_callbacks(self):
  for E in(L51,L53):
   f=self.world(E,True);self.arm(f);token=f.w.settlementBank.operations['2'].token
   self.step(f);self.assertEqual(f.found_count(),1)
   for _ in range(6):self.step(f)
   self.assertEqual((f.found_count(),f.w.settlementBank.operations['2'].token),(1,token))

 def test_deferred_found_rechecks_live_final_permissions(self):
  cases=('TestWorld.formation=2','TestWorld.unitAlias=true','TestWorld.cityEffect=true',
   'UnitManager.CanStartOperation=function()return false end','Game.GetLocalPlayer=function()return 8 end','TestWorld.turn=2')
  for E in(L51,L53):
   for change in cases:
    with self.subTest(E=E.__module__,change=change):
     f=self.world(E,True);self.arm(f);f.lua.execute(change)
     for _ in range(5):self.step(f)
     self.assertEqual(f.found_count(),0);self.assertEqual(f.w.settlementBank.operations['2'].stage,'ARMED')

 def test_ui_reload_does_not_reconstruct_a_live_grant_from_armed(self):
  for E in(L51,L53):
   f=self.world(E,True);self.arm(f);token=f.w.settlementBank.operations['2'].token;f.c.Shutdown()
   f.lua.execute(source(C));f.c=f.lua.globals().BaiqiController
   for _ in range(5):self.step(f)
   self.assertEqual((f.found_count(),f.w.settlementBank.operations['2'].token),(0,token))

 def test_native_writer_replacement_blocks_deferred_grant(self):
  for E in(L51,L53):
   f=self.world(E,True);self.arm(f)
   f.lua.execute('local request=UnitManager.RequestOperation;UnitManager.RequestOperation=function(u,op,p)if op==11 then TestWorld.writerEntries=(TestWorld.writerEntries or 0)+1;error("UNKNOWN_NATIVE_FOUND")end;return request(u,op,p)end')
   # Binding replacement itself closes the original live grant, before entry.
   for _ in range(5):self.step(f)
   self.assertEqual((f.w.writerEntries or 0,f.found_count()),(0,0))

 def test_unknown_native_found_is_entered_once_and_never_replayed(self):
  for E in(L51,L53):
   f=self.world(E,True)
   f.lua.execute('local request=UnitManager.RequestOperation;UnitManager.RequestOperation=function(u,op,p)if op==11 then TestWorld.writerEntries=(TestWorld.writerEntries or 0)+1;error("UNKNOWN_NATIVE_FOUND")end;return request(u,op,p)end')
   self.arm(f)
   for _ in range(5):self.step(f)
   f.w.turn+=1
   for _ in range(5):self.step(f)
   self.assertEqual((f.w.writerEntries,f.found_count(),f.w.settlementBank.operations['2'].stage),(1,0,'ARMED'))

 def test_observation_only_callbacks_never_advance_found_dispatch(self):
  for E in(L51,L53):
   f=self.world(E,True);self.arm(f)
   for _ in range(4):f.c.RunNow(False)
   self.assertEqual(f.found_count(),0)
   self.step(f);self.assertEqual(f.found_count(),1)
