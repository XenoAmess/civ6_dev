"""Retained project investment is selected by the actual guarded city writer."""
from pathlib import Path
import os
import unittest
import test_baiqi_power_project as power


class ProjectResumeTests(unittest.TestCase):
    def setUp(self):
        fixture=power.PowerProjectTests(methodName='runTest');fixture.setUp()
        self.case=fixture.case
        self.case.change(r'''
local w=TestWorld;w.powered=true;w.projectProgress=143;w.projectCost=168;w.projectReads=0
for _,city in ipairs(w.cities)do
 local get=city.GetBuildQueue
 city.GetBuildQueue=function(self)
  local q=get(self);local bp,bc=q.GetBuildingProgress,q.GetBuildingCost
  q.GetProjectProgress=function(_,i)
   w.projectReads=w.projectReads+1
   if w.throwProject then error('project progress unavailable')end
   if w.prayerResume then local r=GameInfo.Projects.PROJECT_ENHANCE_DISTRICT_HOLY_SITE
    if r and i==r.Index then return 8 end end
   if i==2 then return w.projectProgress end
   if i==3 and w.standbyResume then return 143 end
   return 0
  end
  q.GetProjectCost=function(_,i)
   if w.throwProjectCost then error('project cost unavailable')end
   if w.prayerResume then local r=GameInfo.Projects.PROJECT_ENHANCE_DISTRICT_HOLY_SITE
    if r and i==r.Index then return 10 end end
   if i==2 then return w.projectCost end
   return 168
  end
  q.GetBuildingProgress=function(obj,i)if i==9 and w.buildingResume then return 73 end;return bp(obj,i)end
  q.GetBuildingCost=function(obj,i)if i==9 and w.buildingResume then return 165 end;return bc(obj,i)end
  return q
 end
end
''')
        for variable,name in [('BAIQI_PROJECT_RESUME_PLANNER','BaiqiPlanner'),('BAIQI_PROJECT_RESUME_CONTROLLER','BaiqiController')]:
            override=os.environ.get(variable)
            if override:self.case.lua.execute(Path(override).read_text(encoding='utf-8'))
        self.case.c=self.case.lua.globals().BaiqiController

    def test_powered_city_resumes_native_project_investment_using_queue_cost(self):
        self.case.change('TestWorld.powerDefinition.Cost=1')
        self.assertEqual(self.case.chosen(),927)

    def test_special_power_and_prayer_investment_have_an_independent_resume_reason(self):
        self.case.change('TestWorld.powered=false;TestWorld.powerShock=function()TestWorld.powered=true end')
        self.assertEqual(self.case.chosen(),927)
        self.setUp();self.case.change('''
TestWorld.projectProgress=0;TestWorld.prayerResume=true
local p=assert(GameInfo.Projects.PROJECT_ENHANCE_DISTRICT_HOLY_SITE);TestWorld.allowed[p.Hash]=true
''')
        expected=self.case.lua.eval('GameInfo.Projects.PROJECT_ENHANCE_DISTRICT_HOLY_SITE.Hash')
        self.assertEqual(self.case.chosen(),expected)

    def test_unknown_invalid_zero_and_finished_investments_keep_ordinary_choice(self):
        for change in ['w.projectProgress=0','w.projectProgress=-1','w.projectProgress=nil',
                       "w.projectProgress='143'",'w.projectProgress=true','w.projectProgress=0/0',
                       'w.projectProgress=math.huge','w.projectProgress=168','w.projectProgress=169',
                       'w.projectCost=0','w.projectCost=-1','w.projectCost=nil',
                       'w.projectCost=math.huge','w.throwProject=true','w.throwProjectCost=true']:
            with self.subTest(change=change):
                self.setUp();self.case.change('local w=TestWorld;'+change)
                self.assertEqual(self.case.chosen(),901)

    def test_building_investment_food_essential_units_and_repairs_keep_priority(self):
        for change,expected in [('TestWorld.buildingResume=true',901),
                                ('TestWorld.foodStock=0;TestWorld.foodSurplus=0',903),
                                ('TestWorld.allowed[100]=true',100),('TestWorld.allowed[101]=true',101),
                                ('TestWorld.cities[1].GetBuildings=function()return {IsPillaged=function(_,i)return i==9 end}end',901)]:
            with self.subTest(change=change):
                self.setUp();self.case.change(change);self.assertEqual(self.case.chosen(),expected)

    def test_investment_is_reserved_before_ordinary_scan_and_project_not_duplicated(self):
        self.case.change("GameInfo.Buildings=setmetatable({}, {__call=function()local i=0;return function()i=i+1;if i<=512 then return {Index=i,Hash=3000+i,BuildingType='INELIGIBLE_'..i,Maintenance=0}end end end})")
        self.assertEqual(self.case.chosen(),927)
        self.assertEqual(self.case.w.qualification[927],3)

    def test_active_legal_queues_are_preserved_without_project_progress_reads(self):
        self.case.change('TestWorld.queues[66]={{BuildingType=9}};TestWorld.queues[67]={{BuildingType=9}}')
        self.case.c.RunNow();self.assertEqual(len(self.case.w.cityRequests),0)
        self.assertEqual(self.case.w.projectReads,0)

    def test_both_native_production_modes_and_final_permission_are_required(self):
        for mode in ['true','false']:
            with self.subTest(mode=mode):
                self.setUp();self.case.change('''
for _,city in ipairs(TestWorld.cities)do local get=city.GetBuildQueue
 city.GetBuildQueue=function(self)local q=get(self);local old=q.CanProduce
 q.CanProduce=function(obj,h,m,...)if h==927 and m=='''+mode+''' then return false end;return old(obj,h,m,...)end
 return q end
end''')
                self.assertEqual(self.case.chosen(),901)
        self.setUp();self.case.change('''
TestWorld.queues[67]={{BuildingType=9}};local old=CityManager.CanStartOperation
CityManager.CanStartOperation=function(c,op,params,...)local result=old(c,op,params,...)
 if params[5]==927 and TestWorld.qualification[927]>=3 then return false end;return result end
''')
        self.case.c.RunNow();self.assertEqual(len(self.case.w.cityRequests),0)

    def test_last_progress_check_rejects_lost_finished_unknown_or_redefined_work(self):
        for change in ['w.projectProgress=0','w.projectProgress=168','w.projectCost=nil',
                       'w.throwProject=true','w.powerDefinition.Index=77','w.powerDefinition.ProjectType="OTHER"']:
            with self.subTest(change=change):
                self.setUp();self.case.change('TestWorld.queues[67]={{BuildingType=9}};TestWorld.lateShock=function()local w=TestWorld;'+change+' end')
                self.case.c.RunNow();self.assertEqual(len(self.case.w.cityRequests),0)
        self.setUp();self.case.change('TestWorld.queues[67]={{BuildingType=9}};TestWorld.lateShock=function()TestWorld.projectProgress=0 end')
        self.case.c.RunNow();self.assertEqual(len(self.case.w.cityRequests),0)
        self.assertEqual(self.case.chosen(),901)

    def test_final_owner_turn_or_queue_change_cannot_hide_behind_resume_reads(self):
        for change in ['w.turn=2','w.cities[1].GetOwner=function()return 8 end',
                       'w.queues[66]={{BuildingType=9},{BuildingType=0}}']:
            with self.subTest(change=change):
                self.setUp();self.case.change('TestWorld.queues[67]={{BuildingType=9}};TestWorld.lateShock=function()local w=TestWorld;'+change+' end')
                self.case.c.RunNow();self.assertEqual(len(self.case.w.cityRequests),0)

    def test_unknown_native_writer_is_not_replayed_across_refresh_or_turn(self):
        self.case.change('TestWorld.queues[67]={{BuildingType=9}}')
        self.case.w.throwWriter=True;self.case.c.RunNow();self.case.w.throwWriter=False
        self.case.c.Update(3);self.case.w.turn=2;self.case.c.RefreshProduction()
        self.case.c.RunNow();self.case.c.RunNow()
        requests=self.case.w.cityRequests
        self.assertEqual(sum(requests[i].params[5]==927 for i in range(1,len(requests)+1)),1)

    def test_standby_investment_is_excluded_but_new_ordinary_project_is_not_blocked(self):
        self.case.change('''
local old=GameInfo.Projects;local p=TestWorld.powerDefinition
local s={Index=3,Hash=928,ProjectType='PROJECT_BAIQI_STANDBY'}
GameInfo.Projects=setmetatable({[3]=s,[928]=s,PROJECT_BAIQI_STANDBY=s},{__index=old,
 __call=function()local i=0;return function()i=i+1;if i==1 then return p elseif i==2 then return s end end end})
TestWorld.projectProgress=0;TestWorld.standbyResume=true;TestWorld.allowed[928]=true
''')
        self.assertEqual(self.case.chosen(),901)
        self.setUp();self.case.change('''
local old=GameInfo.Projects;local p={Index=5,Hash=930,ProjectType='PROJECT_NEW_ORDINARY'}
GameInfo.Projects=setmetatable({[5]=p,[930]=p},{__index=old,__call=function()local once=false;return function()if not once then once=true;return p end end end})
local oldBuildings=GameInfo.Buildings
GameInfo.Buildings=setmetatable({}, {__index=oldBuildings,__call=function()return function()end end})
TestWorld.projectProgress=0;TestWorld.allowed[930]=true
for row in GameInfo.Districts()do TestWorld.allowed[row.Hash]=false end
''')
        self.assertEqual(self.case.chosen(),930)

    def test_pure_hint_uses_a_bounded_rank_and_preserves_higher_base(self):
        score=self.case.lua.globals().BaiqiPlanner.ResumeProjectScore
        self.assertEqual(score(1,143,168),92.5);self.assertEqual(score(96,143,168),96)
        self.assertGreater(score(1,143,168),92);self.assertLess(score(1,143,168),93)
        for args in [(1,None,168),(1,143,None),(1,0,168),(1,168,168),
                     (1,143,0),(1,float('nan'),168),(1,143,float('inf')),(1,True,168)]:
            with self.subTest(args=args):self.assertEqual(score(*args),1)


if __name__=='__main__':unittest.main()
