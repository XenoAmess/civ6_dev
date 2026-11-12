"""Known unpowered cities can use native projects with zero or positive fuel."""
from pathlib import Path
import os
import unittest
import test_baiqi_food_production as food


class PowerProjectTests(unittest.TestCase):
    def setUp(self):
        fixture=food.FoodProductionTests(methodName='runTest');fixture.setUp()
        self.case=fixture.case
        self.case.change('''
local w=TestWorld
w.foodStock=10;w.foodSurplus=5;w.requiredPower=3;w.powered=false
w.fuel={RESOURCE_COAL=0,RESOURCE_OIL=0,RESOURCE_URANIUM=0};w.powerReads=0
local old=GameInfo.Projects
local p={Index=2,Hash=927,ProjectType='PROJECT_ENHANCE_DISTRICT_INDUSTRIAL_ZONE',PrereqDistrict='DISTRICT_INDUSTRIAL_ZONE'}
w.powerDefinition=p
GameInfo.Projects=setmetatable({[2]=p,[927]=p,PROJECT_ENHANCE_DISTRICT_INDUSTRIAL_ZONE=p},{
 __index=old,__call=function()local nextRow=old();local done=false
  return function()local r=nextRow();if r then return r end;if not done then done=true;return p end end
 end})
w.powerRule={ProjectType=p.ProjectType,FullyPoweredWhileActive=true,RequiredPowerWhileActive=0}
GameInfo.Projects_XP2={[p.ProjectType]=w.powerRule};w.allowed[927]=true
for _,c in ipairs(w.cities)do c.GetPower=function()
 w.powerReads=w.powerReads+1
 if w.powerReadShock then w.powerReadShock()end
 return {GetRequiredPower=function()if w.throwPower then error('native power read')end;return w.requiredPower end,
  IsFullyPowered=function()return w.powered end}
end end
w.objects.player.GetResources=function()return {GetResourceAmount=function(_,typ)
 assert(typ=='RESOURCE_COAL'or typ=='RESOURCE_OIL'or typ=='RESOURCE_URANIUM')
 if w.throwFuel then error('native resource read')end;return w.fuel[typ]
end}end
local can=CityManager.CanStartOperation
CityManager.CanStartOperation=function(c,op,params,...)
 local v=can(c,op,params,...)
 if params[5]==927 then
  if w.qualification[927]==2 and w.powerShock then w.powerShock()end
  if w.qualification[927]==3 and w.lateShock then w.lateShock()end
  if w.rejectPower then return false end
 end
 return v
end
''')
        override=os.environ.get('BAIQI_POWER_CONTROLLER')
        if override:
            self.case.lua.execute(Path(override).read_text(encoding='utf-8'))
            self.case.c=self.case.lua.globals().BaiqiController

    def test_known_unpowered_fuel_empty_city_prefers_native_power_project(self):
        self.assertEqual(self.case.chosen(),927)

    def test_known_power_or_no_demand_keeps_ordinary_production(self):
        for change in ('TestWorld.powered=true','TestWorld.requiredPower=0'):
            with self.subTest(change=change):
                self.setUp();self.case.change(change);self.assertEqual(self.case.chosen(),901)

    def test_unknown_power_and_fuel_never_become_zero(self):
        for change in ('TestWorld.powered=nil','TestWorld.powered=0',
                       'TestWorld.requiredPower=nil','TestWorld.requiredPower=math.huge',
                       'TestWorld.requiredPower=0/0','TestWorld.throwPower=true',
                       'TestWorld.fuel.RESOURCE_COAL=nil','TestWorld.fuel.RESOURCE_OIL=-1',
                       "TestWorld.fuel.RESOURCE_URANIUM='0'",'TestWorld.throwFuel=true',
                       'for _,c in ipairs(TestWorld.cities)do c.GetPower=nil end'):
            with self.subTest(change=change):
                self.setUp();self.case.change(change);self.assertEqual(self.case.chosen(),901)

    def test_actual_project_rule_and_prerequisite_are_required(self):
        for change in ('GameInfo.Projects_XP2=nil','TestWorld.powerRule.FullyPoweredWhileActive=false',
                       'TestWorld.powerRule.RequiredPowerWhileActive=1',
                       "TestWorld.powerRule.ProjectType='OTHER'",
                       "TestWorld.powerDefinition.PrereqDistrict='OTHER'",
                       'TestWorld.powerDefinition.Hash=math.huge'):
            with self.subTest(change=change):
                self.setUp();self.case.change(change);self.assertEqual(self.case.chosen(),901)

    def test_original_legality_and_operation_gates_still_apply(self):
        for change in ('TestWorld.allowed[927]=false','TestWorld.rejectPower=true',
                       "local old=TestWorld.cities[1].GetBuildQueue;TestWorld.cities[1].GetBuildQueue=function(self)local q=old(self);local f=q.CanProduce;q.CanProduce=function(o,h,mode,...)if h==927 and mode==false then return false end;return f(o,h,mode,...)end;return q end;TestWorld.queues[67]={{BuildingType=9}}"):
            with self.subTest(change=change):
                self.setUp();self.case.change(change);self.case.c.RunNow()
                for i in range(1,len(self.case.w.cityRequests)+1):
                    self.assertNotEqual(self.case.w.cityRequests[i].params[5],927)

    def test_demand_or_fuel_changes_at_final_check_replan_same_turn(self):
        for change in ('w.powered=true','w.requiredPower=0','w.fuel.RESOURCE_COAL=-1',
                       'w.fuel.RESOURCE_OIL=nil','w.powerRule.FullyPoweredWhileActive=false'):
            with self.subTest(change=change):
                self.setUp();self.case.change('TestWorld.queues[67]={{BuildingType=9}};TestWorld.powerShock=function()local w=TestWorld;'+change+' end')
                self.case.c.RunNow();self.assertEqual(len(self.case.w.cityRequests),0)
                self.assertEqual(self.case.chosen(),901)

    def test_final_read_cannot_cover_queue_turn_or_owner_change(self):
        for change in ('w.queues[66]={{BuildingType=9},{BuildingType=0}}',
                       'w.turn=2','w.cities[1].GetOwner=function()return 8 end'):
            with self.subTest(change=change):
                self.setUp();self.case.change('TestWorld.queues[67]={{BuildingType=9}};TestWorld.lateShock=function()local w=TestWorld;'+change+' end')
                self.case.c.RunNow();self.assertEqual(len(self.case.w.cityRequests),0)

    def test_food_essential_production_and_repairs_keep_their_priority(self):
        for change,expected in (('TestWorld.foodStock=0;TestWorld.foodSurplus=0',903),
                                ('TestWorld.allowed[100]=true',100),
                                ('TestWorld.allowed[101]=true',101),
                                ('TestWorld.cities[1].GetBuildings=function()return {IsPillaged=function(_,i)return i==9 end}end',901)):
            with self.subTest(change=change):
                self.setUp();self.case.change(change);self.assertEqual(self.case.chosen(),expected)

    def test_existing_queues_are_preserved_without_power_reads(self):
        self.case.change('TestWorld.queues[66]={{BuildingType=9}};TestWorld.queues[67]={{BuildingType=9}}')
        self.case.c.RunNow();self.assertEqual(len(self.case.w.cityRequests),0)
        self.assertEqual(self.case.w.powerReads,0)

    def test_native_request_unknown_is_never_replayed(self):
        self.case.w.throwWriter=True;self.case.c.RunNow();self.case.w.throwWriter=False
        self.case.c.Update(3);self.case.w.turn=2;self.case.c.RunNow();self.case.c.RunNow()
        self.assertEqual(sum(self.case.w.cityRequests[i].params[5]==927 for i in range(1,len(self.case.w.cityRequests)+1)),1)

    def test_power_hint_is_reserved_before_ordinary_scan_budget(self):
        self.case.change("GameInfo.Buildings=setmetatable({}, {__call=function()local i=0;return function()i=i+1;if i<=512 then return {Index=i,Hash=3000+i,BuildingType='INELIGIBLE_'..i,Maintenance=0}end end end})")
        self.assertEqual(self.case.chosen(),927)

    def test_score_only_accepts_positive_known_unpowered_demand_and_known_nonnegative_fuels(self):
        score=self.case.lua.globals().BaiqiPlanner.PowerProjectScore
        self.assertEqual(score(1,3,False,0,0,0),92)
        self.assertEqual(score(100,3,False,0,0,0),100)
        for args in ((1,None,False,0,0,0),(1,3,None,0,0,0),(1,3,False,-1,0,0),
                     (1,3,False,0,float('nan'),0),(1,3,False,0,0,float('inf'))):
            with self.subTest(args=args):self.assertEqual(score(*args),1)


if __name__=='__main__':unittest.main()
