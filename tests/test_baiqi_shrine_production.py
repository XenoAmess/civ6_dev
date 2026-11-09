"""Exercise shrine ranking through the actual city writer and native gates."""
from pathlib import Path
import os
import unittest
import test_baiqi_prayer_production as prayer


class ShrineProductionTests(unittest.TestCase):
    def setUp(self):
        base = prayer.PrayerProductionTests(methodName='runTest')
        base.setUp()
        self.case = base
        base.change('''
local w=TestWorld
w.created=1;w.allowed[902]=true
local old=GameInfo.Buildings
local shrine={Index=2,Hash=902,BuildingType='BUILDING_SHRINE',Maintenance=1}
GameInfo.Buildings=setmetatable({[2]=shrine,[902]=shrine,BUILDING_SHRINE=shrine}, {
 __index=old,__call=function()
  local nextRow=old();local done=false
  return function()
   local row=nextRow();if row then return row end
   if not done then done=true;return shrine end
  end
 end})
for _,city in ipairs(w.cities)do
 local get=city.GetBuildQueue
 city.GetBuildQueue=function()
  local q=get();local can=q.CanProduce
  q.CanProduce=function(self,hash,exclude,...)
   if hash==902 and(not w.completed[city:GetID()]or(exclude==false and w.rejectShrineSecondMode))then return false end
   return can(self,hash,exclude,...)
  end
  return q
 end
end
''')
        # The same production harness can run against the exact previous source.
        override = os.environ.get('BAIQI_SHRINE_CONTROLLER')
        if override:
            base.lua.execute(Path(override).read_text(encoding='utf-8'))
            base.c = base.lua.globals().BaiqiController

    def test_legal_shrine_beats_workshop_and_campus_after_founding(self):
        self.assertEqual(self.case.chosen(), 902)

    def test_essential_production_and_repairs_still_win(self):
        for value in (100, 101, 202, 'repair'):
            with self.subTest(value=value):
                self.setUp()
                if value == 'repair':
                    self.case.change('TestWorld.cities[1].GetBuildings=function()return {IsPillaged=function(_,i)return i==9 end}end')
                    expected = 901
                else:
                    self.case.w.allowed[value] = True
                    expected = value
                    if value == 202:
                        self.case.change('TestWorld.objects.player.GetTreasury=function()return {GetGoldBalance=function()return 1000 end,GetGoldYield=function()return 100 end,GetTotalMaintenance=function()return 0 end}end')
                self.assertEqual(self.case.chosen(), expected)

    def test_existing_prayer_wins_equal_score_before_founding(self):
        self.case.w.created = -1
        self.assertEqual(self.case.chosen(), 910)

    def test_native_prerequisites_second_mode_budget_and_existing_queue_remain_authoritative(self):
        for change in ('TestWorld.completed[66]=false;TestWorld.completed[67]=false',
                       'TestWorld.rejectShrineSecondMode=true',
                       'TestWorld.objects.player.GetTreasury=function()return {GetGoldBalance=function()return 1000 end,GetGoldYield=function()return 1 end,GetTotalMaintenance=function()return 0 end}end',
                       'TestWorld.queues[66]={{BuildingType=9}};TestWorld.queues[67]={{BuildingType=9}}'):
            with self.subTest(change=change):
                self.setUp(); self.case.change(change)
                self.case.c.RunNow()
                for i in range(1, len(self.case.w.cityRequests)+1):
                    self.assertNotEqual(self.case.w.cityRequests[i].params[2], 902)
                self.assertEqual(len(self.case.w.unitRequests), 0)


if __name__ == '__main__':
    unittest.main()
