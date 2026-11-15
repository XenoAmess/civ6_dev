import unittest
from tests import test_baiqi_first_holy_site as holy


class CandidatePruningTests(unittest.TestCase):
    def setUp(self):
        self.case=holy.FirstHolySiteTests(methodName='runTest');self.case.setUp()
        self.lua,self.w,self.c=self.case.lua,self.case.w,self.case.c
        self.lua.execute('''local w=TestWorld;w.quoteReads={};w.placementReads={}
for _,city in ipairs(w.cities)do
 local get=city.GetBuildQueue
 city.GetBuildQueue=function(c)local q=get(c);local can=q.CanProduce
  q.CanProduce=function(self,hash,...)w.quoteReads[hash]=(w.quoteReads[hash]or 0)+1;return can(self,hash,...)end
  return q
 end
end
for _,p in pairs(w.plots)do local f=p.CanHaveDistrict
 p.CanHaveDistrict=function(self,index,...)w.placementReads[index]=(w.placementReads[index]or 0)+1;return f(self,index,...)end
end
function w.AddBuilding(hash,index,kind)
 local old=GameInfo.Buildings;local row={Hash=hash,Index=index,BuildingType=kind,Maintenance=0}
 GameInfo.Buildings=setmetatable({[hash]=row,[index]=row,[kind]=row},{__index=old,__call=function()
  local nextOld=old();local done=false;return function()local r=nextOld();if r then return r end;if not done then done=true;return row end end
 end});w.allowed[hash]=true
end''')

    def test_dominated_building_never_reads_native_production_eligibility(self):
        self.lua.execute("TestWorld.AddBuilding(902,10,'BUILDING_TEST_LOW')")
        self.assertEqual(self.case.chosen(),777)
        self.assertEqual(self.w.quoteReads[902]or 0,0)

    def test_dominated_district_never_scans_placement_tiles(self):
        self.assertEqual(self.case.chosen(),777)
        self.assertEqual(self.w.placementReads[4]or 0,0)

    def test_later_higher_priority_candidate_remains_eligible(self):
        self.lua.execute("TestWorld.allowed[777]=false;TestWorld.allowed[778]=false;TestWorld.AddBuilding(902,10,'BUILDING_SHRINE')")
        self.assertEqual(self.case.chosen(),902)
        self.assertGreater(self.w.quoteReads[902],0)

    def test_equal_score_keeps_the_earliest_candidate(self):
        self.lua.execute("TestWorld.allowed={};TestWorld.AddBuilding(902,10,'BUILDING_TEST_A');TestWorld.AddBuilding(903,11,'BUILDING_TEST_B')")
        self.assertEqual(self.case.chosen(),902)
        self.assertEqual(self.w.quoteReads[903]or 0,0)

    def test_repair_outweighs_an_existing_normal_candidate(self):
        self.lua.execute("TestWorld.AddBuilding(902,10,'BUILDING_TEST_LOW');TestWorld.cities[1].GetBuildings=function()return {IsPillaged=function(_,i)return i==10 end}end")
        self.assertEqual(self.case.chosen(),902)

    def test_pruned_pool_still_rejects_a_failed_final_native_check(self):
        self.lua.execute('''TestWorld.allowed[777]=false;TestWorld.allowed[778]=false
local old=CityManager.CanStartOperation;local count=0
CityManager.CanStartOperation=function(city,op,params,...)
 if params[2]==901 then count=count+1;if count==2 then return false end end
 return old(city,op,params,...)
end''')
        self.c.RunNow();self.assertEqual(len(self.w.cityRequests),0)


if __name__=='__main__':unittest.main()
