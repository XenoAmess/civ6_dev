"""Known amenity shortages affect ranking through the real city writer."""
import unittest
import test_baiqi_prayer_production as prayer


class AmenityProductionTests(unittest.TestCase):
    def setUp(self):
        self.case = prayer.PrayerProductionTests(methodName='runTest')
        self.case.setUp()
        self.case.change('''
local w=TestWorld
w.created=1;w.amenities=3;w.needed=5;w.growthReads=0
local function append(kind,row,key)
 local old=GameInfo[kind]
 GameInfo[kind]=setmetatable({[row.Index]=row,[row.Hash]=row,[row[key]]=row}, {
  __index=old,__call=function()
   local nextRow=old();local done=false
   return function()local r=nextRow();if r then return r end
    if not done then done=true;return row end end
  end})
end
append('Buildings',{Index=2,Hash=903,BuildingType='BUILDING_ARENA',Entertainment=2,Maintenance=1},'BuildingType')
append('Districts',{Index=5,Hash=779,DistrictType='DISTRICT_ENTERTAINMENT_COMPLEX',Entertainment=1},'DistrictType')
w.allowed[903]=true;w.allowed[779]=false
for _,city in ipairs(w.cities)do
 city.GetGrowth=function(self)
  assert(self==city);w.growthReads=w.growthReads+1
  if w.throwGrowth then error('growth unavailable')end
  return {GetAmenities=function()return w.amenities end,GetAmenitiesNeeded=function()return w.needed end}
 end
 local get=city.GetBuildQueue
 city.GetBuildQueue=function(self)
  local q=get(self);local can=q.CanProduce;local placed=q.HasBeenPlaced
  q.HasBeenPlaced=function(obj,hash)if hash==779 then return false end;return placed(obj,hash)end
  q.CanProduce=function(obj,hash,mode,...)
   if(hash==903 or hash==779)and((mode==true and w.rejectFirst)or(mode==false and w.rejectSecond))then return false end
   return can(obj,hash,mode,...)
  end
  return q
 end
end
for _,plot in pairs(w.plots)do
 local can=plot.CanHaveDistrict
 plot.CanHaveDistrict=function(self,index,pid,cid)
  if index==5 then assert(pid==7 and cid==self:GetIndex()+24);return not w.noPlacement end
  return can(self,index,pid,cid)
 end
end
local can=CityManager.CanStartOperation
CityManager.CanStartOperation=function(city,op,params,...)
 local result=can(city,op,params,...)
 local hash=params[2]or params[3]
 if(hash==903 or hash==779)and w.rejectFinal and w.qualification[hash]==2 then return false end
 return result
end
''')

    def venue(self, district=False):
        self.case.w.allowed[903] = not district
        self.case.w.allowed[779] = district
        return 779 if district else 903

    def test_legal_arena_and_entertainment_district_beat_workshop_during_shortage(self):
        for district in (False, True):
            with self.subTest(district=district):
                self.setUp()
                expected = self.venue(district)
                self.assertEqual(self.case.chosen(), expected)

    def test_mild_or_unknown_shortage_and_failed_growth_reads_keep_ordinary_choice(self):
        for change in ('TestWorld.amenities=4', 'TestWorld.amenities=nil',
                       "TestWorld.amenities='3'", 'TestWorld.needed=math.huge',
                       'TestWorld.throwGrowth=true',
                       'for _,c in ipairs(TestWorld.cities)do c.GetGrowth=nil end'):
            with self.subTest(change=change):
                self.setUp(); self.case.change(change)
                self.assertEqual(self.case.chosen(), 901)

    def test_essential_production_keeps_higher_priority(self):
        for value in (100, 101, 202):
            with self.subTest(value=value):
                self.setUp(); self.case.w.allowed[value] = True
                if value == 202:
                    self.case.change('TestWorld.objects.player.GetTreasury=function()return {GetGoldBalance=function()return 1000 end,GetGoldYield=function()return 100 end,GetTotalMaintenance=function()return 0 end}end')
                self.assertEqual(self.case.chosen(), value)

    def test_repairs_remain_above_amenity_construction(self):
        self.case.change('TestWorld.cities[1].GetBuildings=function()return {IsPillaged=function(_,i)return i==9 end}end')
        self.assertEqual(self.case.chosen(), 901)

    def test_native_two_modes_and_placement_still_reject_candidates(self):
        for district, flag in ((False, 'rejectFirst'), (False, 'rejectSecond'),
                               (True, 'rejectFirst'), (True, 'rejectSecond'),
                               (True, 'noPlacement')):
            with self.subTest(district=district, flag=flag):
                self.setUp(); self.venue(district); self.case.w[flag] = True
                self.assertEqual(self.case.chosen(), 901)

    def test_final_native_legality_change_prevents_any_write(self):
        self.case.w.rejectFinal = True
        self.case.change('TestWorld.queues[67]={{BuildingType=9},{BuildingType=0}}')
        self.case.c.RunNow()
        self.assertEqual(len(self.case.w.cityRequests), 0)
        self.assertEqual(len(self.case.w.unitRequests), 0)

    def test_arena_maintenance_budget_still_blocks_unaffordable_choice(self):
        self.case.change('TestWorld.objects.player.GetTreasury=function()return {GetGoldBalance=function()return 1000 end,GetGoldYield=function()return 1 end,GetTotalMaintenance=function()return 0 end}end')
        self.assertEqual(self.case.chosen(), 901)

    def test_existing_queues_are_untouched_and_do_not_read_growth(self):
        self.case.change('TestWorld.queues[66]={{BuildingType=9},{BuildingType=0}};TestWorld.queues[67]={{BuildingType=9},{BuildingType=0}}')
        self.case.c.RunNow()
        self.assertEqual(len(self.case.w.cityRequests), 0)
        self.assertEqual(len(self.case.w.unitRequests), 0)
        self.assertEqual(self.case.w.growthReads, 0)
        self.assertEqual(len(self.case.w.queues[66]), 2)

    def test_pure_score_handles_finite_inputs_and_preserves_higher_priorities(self):
        score = self.case.lua.globals().BaiqiPlanner.AmenityProductionScore
        self.assertEqual(score(40, 2, 3, 5), 94)
        self.assertEqual(score(110, 2, 3, 5), 110)
        self.assertEqual(score(40, 1, -2, 0), 94)
        for values in ((40, 0, 3, 5), (40, 2, 4, 5), (40, 2, 3, -1),
                       (40, None, 3, 5), (40, 2, float('nan'), 5),
                       (40, 2, 3, float('inf')), (40, '2', 3, 5)):
            with self.subTest(values=values):
                self.assertEqual(score(*values), 40)
        self.assertEqual(score('unknown', 2, 3, 5), 'unknown')


if __name__ == '__main__':
    unittest.main()
