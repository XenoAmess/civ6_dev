"""A flooded district may block a retained building; use the real writer."""
from pathlib import Path
import os
import unittest
import test_baiqi_prayer_production as prayer


class BlockedBuildingQueueTests(unittest.TestCase):
    def setUp(self):
        self.case = prayer.PrayerProductionTests(methodName='runTest')
        self.case.setUp()
        self.case.change('''
local w=TestWorld
w.created=1;w.blockedPillaged=true;w.blockedBuilt=false;w.blockedKnown=true
w.blockedAllowed=false;w.blockedProgress=73;w.blockedCost=165
w.allowed={[901]=true};w.logs={}
print=function(...)local p={};for i=1,select('#',...)do p[i]=tostring(select(i,...))end;w.logs[#w.logs+1]=table.concat(p,' ')end
CityOperationTypes.VALUE_PREPEND=970587057
w.oldEntry={BuildingType=25,Directive=1,Modifiers=0,Location={x=-1,y=-1}}
w.queues[66]={w.oldEntry};w.queues[67]={{BuildingType=9}}
local factory={Index=25,Hash=902,BuildingType='BUILDING_FACTORY',PrereqDistrict='DISTRICT_CAMPUS',Maintenance=3}
GameInfo.Buildings[25]=factory;GameInfo.Buildings[902]=factory
for _,c in ipairs(w.cities)do
 local gb=c.GetBuildings;c.GetBuildings=function()
  local b=gb();b.HasBuilding=function(_,i)if w.throwBlocked then error('asset unavailable')end;if i==25 then return w.blockedBuilt end;return false end;return b
 end
 local gd=c.GetDistricts;c.GetDistricts=function()
  local d=gd();local has=d.HasDistrict;local pill=d.IsPillaged
  d.HasDistrict=function(self,i,...)if i==4 then return w.blockedKnown end;return has(self,i,...)end
  d.IsPillaged=function(self,i)if i==4 then return w.blockedPillaged end;return pill(self,i)end
  return d
 end
 local gq=c.GetBuildQueue;c.GetBuildQueue=function()
  local q=gq();local can=q.CanProduce
  q.CanProduce=function(self,hash,mode,...)
   if hash==902 then if mode==true then return w.blockedKnown end;return w.blockedAllowed end
   if hash==901 and((mode==true and w.rejectFirst)or(mode==false and w.rejectSecond))then return false end
   return can(self,hash,mode,...)
  end
  q.GetBuildingProgress=function(_,i)assert(i==25);return w.blockedProgress end
  q.GetBuildingCost=function(_,i)assert(i==25);return w.blockedCost end
  return q
 end
end
local can=CityManager.CanStartOperation
CityManager.CanStartOperation=function(c,op,params,...)
 local result=can(c,op,params,...)
 if params[2]==901 then
  if w.qualification[901]==2 and w.shock then w.shock()end
  if w.rejectFinal and w.qualification[901]>=2 then return false end
 end
 return result and not w.rejectOperation
end
local writer=CityManager.RequestOperation
CityManager.RequestOperation=function(c,op,params)
 writer(c,op,params)
 if w.applyWriter then
  assert(params[CityOperationTypes.PARAM_INSERT_MODE]==CityOperationTypes.VALUE_PREPEND and params[2]==901)
  table.insert(w.queues[c:GetID()],1,{BuildingType=9,Directive=1,Modifiers=0})
  w.current[c:GetID()]=901
 end
end
''')
        override = os.environ.get('BAIQI_BLOCKED_CONTROLLER')
        if override:
            self.case.lua.execute(Path(override).read_text(encoding='utf-8'))
            self.case.c = self.case.lua.globals().BaiqiController

    def logs(self):
        return '\n'.join(self.case.w.logs.values())

    def test_prepend_preserves_factory_entry_and_progress(self):
        self.case.w.applyWriter = True
        self.assertEqual(self.case.chosen(), 901)
        self.case.change('assert(TestWorld.queues[66][2]==TestWorld.oldEntry)')
        self.assertEqual(self.case.w.blockedProgress, 73)
        insert_key=self.case.lua.globals().CityOperationTypes.PARAM_INSERT_MODE
        self.assertEqual(self.case.w.cityRequests[1].params[insert_key], 970587057)
        self.case.c.RunNow()
        self.assertIn('queue_observed', self.logs())
        self.assertEqual(len(self.case.w.cityRequests), 1)

    def test_no_preemption_of_active_or_multiple_entries(self):
        for change in ('TestWorld.current[66]=902',
                       'TestWorld.queues[66][2]={BuildingType=9}'):
            with self.subTest(change=change):
                self.setUp();self.case.change(change);self.case.c.RunNow()
                self.assertEqual(len(self.case.w.cityRequests), 0)

    def test_normal_buildable_or_unpillaged_or_owned_asset_is_preserved(self):
        for change in ('TestWorld.blockedAllowed=true', 'TestWorld.blockedPillaged=false',
                       'TestWorld.blockedBuilt=true', 'TestWorld.blockedProgress=165'):
            with self.subTest(change=change):
                self.setUp();self.case.change(change);self.case.c.RunNow()
                self.assertEqual(len(self.case.w.cityRequests), 0)

    def test_unknown_reads_or_bad_head_never_authorize_prepend(self):
        for change in ('TestWorld.blockedKnown=nil', 'TestWorld.blockedBuilt=nil',
                       'TestWorld.blockedPillaged=nil', 'TestWorld.blockedAllowed=nil',
                       'TestWorld.throwBlocked=true', 'TestWorld.blockedCost=0/0',
                       'TestWorld.blockedProgress=-1', 'TestWorld.oldEntry.UnitType=0',
                       'TestWorld.oldEntry.Directive=nil', 'TestWorld.oldEntry.Location.x=math.huge',
                       'GameInfo.Buildings[25].PrereqDistrict=nil',
                       'CityOperationTypes.VALUE_PREPEND=nil', 'CityOperationTypes.VALUE_PREPEND="bad"'):
            with self.subTest(change=change):
                self.setUp();self.case.change(change);self.case.c.RunNow()
                self.assertEqual(len(self.case.w.cityRequests), 0)

    def test_signature_or_prerequisite_change_at_final_gate_stops_write(self):
        for shock in ('w.oldEntry.Modifiers=1', 'w.oldEntry.Location.x=3',
                      'w.blockedPillaged=false', 'w.blockedAllowed=true',
                      'w.current[66]=902', 'w.queues[66][2]={BuildingType=9}'):
            with self.subTest(shock=shock):
                self.setUp();self.case.change('TestWorld.shock=function()local w=TestWorld;'+shock+' end')
                self.case.c.RunNow();self.assertEqual(len(self.case.w.cityRequests), 0)

    def test_original_native_modes_and_operation_rejection_are_authoritative(self):
        for flag in ('rejectFirst', 'rejectSecond', 'rejectFinal', 'rejectOperation'):
            with self.subTest(flag=flag):
                self.setUp();self.case.w[flag]=True;self.case.c.RunNow()
                self.assertEqual(len(self.case.w.cityRequests), 0)

    def test_pending_unobserved_or_unknown_writer_is_not_replayed(self):
        for throws in (False, True):
            with self.subTest(throws=throws):
                self.setUp();self.case.w.throwWriter=throws;self.case.c.RunNow()
                self.case.w.throwWriter=False;self.case.c.Update(3)
                self.case.w.turn=2;self.case.c.RunNow();self.case.c.RunNow()
                self.assertEqual(len(self.case.w.cityRequests), 1)
                self.assertIn('error' if throws else 'queue_prepend_unresolved', self.logs())

    def test_candidate_in_second_position_does_not_prove_success(self):
        self.assertEqual(self.case.chosen(), 901)
        self.case.change('TestWorld.queues[66][2]={BuildingType=9};TestWorld.current[66]=901')
        self.case.c.Update(3)
        self.assertNotIn('queue_observed', self.logs())
        self.assertIn('queue_prepend_unresolved', self.logs())

    def test_changed_retained_entry_does_not_prove_success(self):
        self.case.w.applyWriter=True
        self.assertEqual(self.case.chosen(), 901)
        self.case.change('TestWorld.oldEntry.Modifiers=1')
        self.case.c.Update(3)
        self.assertNotIn('queue_observed', self.logs())
        self.assertIn('queue_prepend_unresolved', self.logs())


if __name__ == '__main__':
    unittest.main()
