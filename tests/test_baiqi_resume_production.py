"""Invested legal buildings compete with repeating power projects at the writer."""
from pathlib import Path
import os
import unittest
import test_baiqi_power_project as power


class ResumeProductionTests(unittest.TestCase):
    def setUp(self):
        fixture=power.PowerProjectTests(methodName='runTest');fixture.setUp()
        self.case=fixture.case
        self.case.change('''
local w=TestWorld;w.resumeProgress=73;w.resumeCost=165;w.resumeReads=0
for _,city in ipairs(w.cities)do
 local get=city.GetBuildQueue
 city.GetBuildQueue=function(self)
  local q=get(self);local gp=q.GetBuildingProgress;local gc=q.GetBuildingCost
  q.GetBuildingProgress=function(obj,i)
   if i==9 then w.resumeReads=w.resumeReads+1;if w.throwResume then error('progress unavailable')end;return w.resumeProgress end
   return gp(obj,i)
  end
  q.GetBuildingCost=function(obj,i)if i==9 then return w.resumeCost end;return gc(obj,i)end
  return q
 end
end
''')
        override=os.environ.get('BAIQI_RESUME_CONTROLLER')
        if override:
            self.case.lua.execute(Path(override).read_text(encoding='utf-8'))
            self.case.c=self.case.lua.globals().BaiqiController

    def test_native_queue_cost_and_investment_beat_repeating_project(self):
        self.case.change('GameInfo.Buildings[901].Cost=50')
        self.assertEqual(self.case.chosen(),901)

    def test_unknown_invalid_zero_or_completed_progress_keeps_project(self):
        for change in ('w.resumeProgress=0','w.resumeProgress=-1','w.resumeProgress=nil',
                       'w.resumeProgress=0/0','w.resumeProgress=math.huge',
                       'w.resumeProgress=165','w.resumeProgress=166','w.resumeCost=nil',
                       'w.resumeCost=0','w.resumeCost=-1','w.resumeCost=math.huge',
                       'w.resumeCost=0/0','w.throwResume=true'):
            with self.subTest(change=change):
                self.setUp();self.case.change('local w=TestWorld;'+change)
                self.assertEqual(self.case.chosen(),927)

    def test_two_original_building_modes_still_control_entry(self):
        for mode in ('true','false'):
            with self.subTest(mode=mode):
                self.setUp();self.case.change('''
for _,city in ipairs(TestWorld.cities)do local get=city.GetBuildQueue
 city.GetBuildQueue=function(self)local q=get(self);local can=q.CanProduce
 q.CanProduce=function(obj,h,m,...)if h==901 and m=='''+mode+''' then return false end;return can(obj,h,m,...)end;return q end
end''')
                self.assertEqual(self.case.chosen(),927)

    def test_final_native_permission_loss_stops_building_writer(self):
        self.case.change('''TestWorld.queues[67]={{BuildingType=9}};local old=CityManager.CanStartOperation
CityManager.CanStartOperation=function(c,op,params,...)local result=old(c,op,params,...)
 if params[2]==901 and TestWorld.qualification[901]>=2 then return false end;return result end''')
        self.case.c.RunNow();self.assertEqual(len(self.case.w.cityRequests),0)

    def test_resume_does_not_override_maintenance_or_essential_production(self):
        self.case.change('GameInfo.Buildings[901].Maintenance=1;TestWorld.objects.player.GetTreasury=function()return {GetGoldBalance=function()return 1000 end,GetGoldYield=function()return 0 end,GetTotalMaintenance=function()return 0 end}end')
        self.assertEqual(self.case.chosen(),927)
        for change,expected in (('TestWorld.foodStock=0;TestWorld.foodSurplus=0',903),
                                 ('TestWorld.allowed[100]=true',100),
                                 ('TestWorld.allowed[101]=true',101)):
            with self.subTest(change=change):
                self.setUp();self.case.change(change);self.assertEqual(self.case.chosen(),expected)

    def test_active_queue_survives_without_extra_progress_reads(self):
        self.case.change('TestWorld.queues[66]={{BuildingType=9}};TestWorld.queues[67]={{BuildingType=9}}')
        self.case.c.RunNow();self.assertEqual(len(self.case.w.cityRequests),0)
        self.assertEqual(self.case.w.resumeReads,0)

    def test_unknown_writer_is_not_replayed_after_turn_change(self):
        self.case.w.throwWriter=True;self.case.c.RunNow();self.case.w.throwWriter=False
        self.case.c.Update(3);self.case.w.turn=2;self.case.c.RunNow();self.case.c.RunNow()
        self.assertEqual(sum(self.case.w.cityRequests[i].params[2]==901 for i in range(1,len(self.case.w.cityRequests)+1)),1)

    def test_score_preserves_higher_priorities_and_repair_dominance(self):
        score=self.case.lua.globals().BaiqiPlanner.ResumeProductionScore
        self.assertEqual(score(40,73,165),93)
        self.assertEqual(score(96,73,165),96)
        choose=self.case.lua.globals().BaiqiPlanner.Choose
        l=self.case.lua
        city=l.table_from({'paused':False,'queueEmpty':True})
        candidates=l.table_from([l.table_from({'legal':True,'score':93,'index':1}),l.table_from({'legal':True,'score':1,'index':2,'repair':True})])
        self.assertEqual(choose(city,candidates).index,2)


if __name__=='__main__':unittest.main()
