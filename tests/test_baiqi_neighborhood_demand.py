"""Housing demand through the real production writer; no queue replacement."""
from pathlib import Path
import os
import unittest
import test_baiqi_prayer_production as prayer


class NeighborhoodDemandTests(unittest.TestCase):
    def setUp(self):
        self.case=prayer.PrayerProductionTests(methodName='runTest')
        self.case.setUp()
        self.case.change('''
local w=TestWorld
w.created=1;w.housing=20;w.population=4;w.housingReads=0
w.allowed={[779]=true,[910]=true}
local old=GameInfo.Districts
local row={Index=5,Hash=779,DistrictType='DISTRICT_NEIGHBORHOOD'}
GameInfo.Districts=setmetatable({[5]=row,[779]=row,DISTRICT_NEIGHBORHOOD=row},{__index=old,__call=function()
 local nextRow=old();local done=false;return function()local r=nextRow();if r then return r end;if not done then done=true;return row end end
end})
for _,c in ipairs(w.cities)do
 c.GetPopulation=function()return w.population end
 c.GetGrowth=function()return {GetHousing=function()
  w.housingReads=w.housingReads+1;if w.throwHousing then error('housing unavailable')end;return w.housing end}end
 local get=c.GetBuildQueue;c.GetBuildQueue=function(self)
  local q=get(self);local placed=q.HasBeenPlaced;local can=q.CanProduce
  q.HasBeenPlaced=function(obj,hash)if hash==779 then return w.placedNeighborhood==true end;return placed(obj,hash)end
  q.CanProduce=function(obj,hash,mode,...)
   if hash==779 and((mode==true and w.rejectFirst)or(mode==false and w.rejectSecond))then return false end
   return can(obj,hash,mode,...)
  end
  return q
 end
end
for _,p in pairs(w.plots)do local can=p.CanHaveDistrict;p.CanHaveDistrict=function(self,index,pid,cid)
 if index==5 then assert(pid==7 and cid==self:GetIndex()+24);return true end;return can(self,index,pid,cid)
end end
local can=CityManager.CanStartOperation
CityManager.CanStartOperation=function(c,op,params,...)
 local r=can(c,op,params,...)
 if params[3]==779 and w.qualification[779]==2 and w.finalHousing~=nil then w.housing=w.finalHousing end
 if params[3]==779 and w.rejectFinal and w.qualification[779]==2 then return false end
 return r
end
''')
        override=os.environ.get('BAIQI_HOUSING_CONTROLLER')
        if override:
            self.case.lua.execute(Path(override).read_text(encoding='utf-8'))
            self.case.c=self.case.lua.globals().BaiqiController

    def test_large_housing_surplus_chooses_existing_project_instead_of_another_neighborhood(self):
        self.assertEqual(self.case.chosen(),910)

    def test_four_citizen_boundary_and_fractional_housing(self):
        for housing,expected in ((8,910),(7.5,779),(7,779),(4,779)):
            with self.subTest(housing=housing):
                self.setUp();self.case.w.housing=housing
                self.assertEqual(self.case.chosen(),expected)

    def test_unknown_values_and_native_exceptions_keep_original_planning(self):
        for change in ('TestWorld.housing=nil',"TestWorld.housing='20'",'TestWorld.housing=true',
                       'TestWorld.housing=math.huge','TestWorld.housing=0/0',
                       'TestWorld.housing=-1','TestWorld.population=0','TestWorld.population=4.5',
                       'TestWorld.throwHousing=true','for _,c in ipairs(TestWorld.cities)do c.GetGrowth=nil end'):
            with self.subTest(change=change):
                self.setUp();self.case.change(change)
                self.assertEqual(self.case.chosen(),779)

    def test_other_districts_do_not_use_housing_gate(self):
        self.case.w.allowed[778]=True
        self.assertEqual(self.case.chosen(),778)

    def test_placed_work_remains_eligible_without_reading_housing(self):
        self.case.w.placedNeighborhood=True
        self.assertEqual(self.case.chosen(),779)
        self.assertEqual(self.case.w.housingReads,0)

    def test_existing_queue_is_untouched_and_skips_demand_reads(self):
        self.case.change('TestWorld.queues[66]={{BuildingType=9},{BuildingType=0}};TestWorld.queues[67]={{BuildingType=9},{BuildingType=0}}')
        self.case.c.RunNow()
        self.assertEqual(len(self.case.w.cityRequests),0)
        self.assertEqual(len(self.case.w.unitRequests),0)
        self.assertEqual(self.case.w.housingReads,0)

    def test_changed_housing_before_write_replans_without_sending_stale_neighborhood(self):
        self.case.change('TestWorld.housing=6;TestWorld.finalHousing=20;TestWorld.queues[67]={{BuildingType=9}}')
        self.case.c.RunNow()
        self.assertEqual(len(self.case.w.cityRequests),0)
        self.assertEqual(self.case.chosen(),910)

    def test_original_two_native_modes_and_final_operation_gate_still_apply(self):
        for flag in ('rejectFirst','rejectSecond','rejectFinal'):
            with self.subTest(flag=flag):
                self.setUp();self.case.w.housing=6;self.case.w[flag]=True
                self.case.change('TestWorld.queues[67]={{BuildingType=9}}')
                self.case.c.RunNow()
                for i in range(1,len(self.case.w.cityRequests)+1):
                    self.assertNotEqual(self.case.w.cityRequests[i].params[3],779)
                self.assertEqual(len(self.case.w.unitRequests),0)


if __name__=='__main__':unittest.main()
