"""Food-supply ranking through the actual city writer and original native gates."""
from pathlib import Path
import os
import unittest
import test_baiqi_prayer_production as prayer


class FoodProductionTests(unittest.TestCase):
    def setUp(self):
        self.case = prayer.PrayerProductionTests(methodName='runTest')
        self.case.setUp()
        self.case.change('''
local w=TestWorld
w.created=1;w.foodStock=0.68359375;w.foodSurplus=0;w.yieldScans=0
local old=GameInfo.Buildings
local market={Index=2,Hash=903,BuildingType='BUILDING_FOOD_MARKET',Maintenance=1}
GameInfo.Buildings=setmetatable({[2]=market,[903]=market,BUILDING_FOOD_MARKET=market}, {
 __index=old,__call=function()
  local nextRow=old();local done=false
  return function()local r=nextRow();if r then return r end
   if not done then done=true;return market end end
 end})
w.allowed[903]=true
w.yieldRows={{BuildingType='BUILDING_FOOD_MARKET',YieldType='YIELD_FOOD',YieldChange=4}}
GameInfo.Building_YieldChanges=function()
 w.yieldScans=w.yieldScans+1;local i=0
 return function()
  i=i+1;if w.throwYield then error('table unavailable')end
  if w.repeatYield then return {BuildingType='OTHER_'..i,YieldType='YIELD_GOLD',YieldChange=1}end
  return w.yieldRows[i]
 end
end
for _,city in ipairs(w.cities)do
 city.GetGrowth=function(self)
  assert(self==city)
  return {GetFoodSurplus=function()
    if w.throwGrowth then error('growth unavailable')end
    return w.foodSurplus end,
   GetFood=function()return w.foodStock end,
   GetAmenities=function()return w.amenities end,
   GetAmenitiesNeeded=function()return w.needed end}
 end
 local get=city.GetBuildQueue
 city.GetBuildQueue=function(self)
  local q=get(self);local can=q.CanProduce
  q.CanProduce=function(obj,hash,mode,...)
   if hash==903 and((mode==true and w.rejectFirst)or(mode==false and w.rejectSecond))then return false end
   return can(obj,hash,mode,...)
  end
  return q
 end
end
local can=CityManager.CanStartOperation
CityManager.CanStartOperation=function(city,op,params,...)
 local result=can(city,op,params,...)
 if params[2]==903 and w.rejectFinal and w.qualification[903]==2 then return false end
 return result
end
''')
        override = os.environ.get('BAIQI_FOOD_PRODUCTION_CONTROLLER')
        if override:
            self.case.lua.execute(Path(override).read_text(encoding='utf-8'))
            self.case.c = self.case.lua.globals().BaiqiController

    def test_legal_food_market_beats_workshop_with_low_reserves(self):
        self.assertEqual(self.case.chosen(), 903)

    def test_surplus_and_stock_boundaries_keep_ordinary_ranking(self):
        for change in ('TestWorld.foodSurplus=1', 'TestWorld.foodStock=2',
                       'TestWorld.foodStock=-1', 'TestWorld.foodSurplus=nil',
                       "TestWorld.foodStock='0'", 'TestWorld.foodStock=math.huge',
                       'TestWorld.throwGrowth=true',
                       'for _,c in ipairs(TestWorld.cities)do c.GetGrowth=nil end'):
            with self.subTest(change=change):
                self.setUp(); self.case.change(change)
                self.assertEqual(self.case.chosen(), 901)

    def test_partial_malformed_missing_or_unbounded_yields_do_not_boost(self):
        for change in ('GameInfo.Building_YieldChanges=nil', 'TestWorld.throwYield=true',
                       'TestWorld.repeatYield=true', 'TestWorld.yieldRows={}',
                       'TestWorld.yieldRows[1].YieldChange=nil',
                       "TestWorld.yieldRows[1].YieldChange='4'",
                       'TestWorld.yieldRows[1].YieldChange=0/0',
                       'TestWorld.yieldRows[1].BuildingType=nil',
                       'TestWorld.yieldRows[2]={BuildingType="OTHER",YieldChange=1}',
                       'TestWorld.yieldRows[2]=TestWorld.yieldRows[1]',
                       'TestWorld.yieldRows[2]=false'):
            with self.subTest(change=change):
                self.setUp(); self.case.change(change)
                self.assertEqual(self.case.chosen(), 901)

    def test_zero_negative_and_nonfood_yields_keep_ordinary_score(self):
        for change in ('TestWorld.yieldRows[1].YieldChange=0',
                       'TestWorld.yieldRows[1].YieldChange=-4',
                       "TestWorld.yieldRows[1].YieldType='YIELD_GOLD'"):
            with self.subTest(change=change):
                self.setUp(); self.case.change(change)
                self.assertEqual(self.case.chosen(), 901)

    def test_both_native_modes_maintenance_and_existing_queues_remain_authoritative(self):
        for change in ('TestWorld.rejectFirst=true', 'TestWorld.rejectSecond=true',
                       'TestWorld.objects.player.GetTreasury=function()return {GetGoldBalance=function()return 1000 end,GetGoldYield=function()return 1 end,GetTotalMaintenance=function()return 0 end}end',
                       'TestWorld.queues[66]={{BuildingType=9},{BuildingType=0}};TestWorld.queues[67]={{BuildingType=9},{BuildingType=0}}'):
            with self.subTest(change=change):
                self.setUp(); self.case.change(change); self.case.c.RunNow()
                self.assertEqual(len(self.case.w.unitRequests), 0)
                for i in range(1, len(self.case.w.cityRequests)+1):
                    self.assertNotEqual(self.case.w.cityRequests[i].params[2], 903)
                if change.startswith('TestWorld.queues'):
                    self.assertEqual(self.case.w.yieldScans, 0)
                    self.assertEqual(len(self.case.w.cityRequests), 0)

    def test_final_qualification_lost_prevents_write(self):
        self.case.change('TestWorld.rejectFinal=true;TestWorld.queues[67]={{BuildingType=9}}')
        self.case.c.RunNow()
        self.assertEqual(len(self.case.w.cityRequests), 0)

    def test_essential_production_repairs_and_amenity_priority_survive(self):
        for value in (100, 101, 202, 'repair', 'amenity'):
            with self.subTest(value=value):
                self.setUp()
                if value == 'repair':
                    self.case.change('TestWorld.cities[1].GetBuildings=function()return {IsPillaged=function(_,i)return i==9 end}end')
                    expected=901
                elif value == 'amenity':
                    # Food metadata cannot erase the existing entertainment boost.
                    self.case.change('GameInfo.Buildings[903].Entertainment=2;TestWorld.amenities=3;TestWorld.needed=5;TestWorld.foodStock=10')
                    expected=903
                else:
                    self.case.w.allowed[value]=True; expected=value
                    if value==202:
                        self.case.change('TestWorld.objects.player.GetTreasury=function()return {GetGoldBalance=function()return 1000 end,GetGoldYield=function()return 100 end,GetTotalMaintenance=function()return 0 end}end')
                self.assertEqual(self.case.chosen(), expected)

    def test_only_low_food_city_scans_yield_table_and_score_is_finite(self):
        self.case.w.foodSurplus=1
        self.assertEqual(self.case.chosen(), 901)
        self.assertEqual(self.case.w.yieldScans, 0)
        score=self.case.lua.globals().BaiqiPlanner.FoodProductionScore
        self.assertEqual(score(40, 4, -1, 0), 94)
        self.assertEqual(score(110, 4, 0, 1.999), 110)
        for args in ((40, None, 0, 0), (40, 4, 0, 2),
                     (40, 0, 0, 0), (40, 4, float('nan'), 0),
                     (40, 4, 0, float('inf'))):
            with self.subTest(args=args): self.assertEqual(score(*args), 40)


if __name__ == '__main__':
    unittest.main()
