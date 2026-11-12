"""Actual city dispatch against independent native-shaped housing contracts."""
from pathlib import Path
import os
import sys
import unittest
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT));sys.path.insert(0,str(ROOT/'tests'))
import test_baiqi_district_food as food

class HousingPlacementTests(unittest.TestCase):
    def setUp(self):
        self.food=food.DistrictFoodTests(methodName='runTest');self.food.setUp()
        self.case=self.food.case;self.lua=self.food.lua;self.w=self.food.w
        self.lua.execute(r'''
local w=TestWorld;local c=w.objects.city
GameInfo.Districts[777].DistrictType='DISTRICT_NEIGHBORHOOD'
GameInfo.Features={
 [3]={Index=3,FeatureType='FEATURE_FOREST',Removable=true,NaturalWonder=false},
 [2]={Index=2,FeatureType='FEATURE_JUNGLE',Removable=true,NaturalWonder=false},
 [0]={Index=0,FeatureType='FEATURE_MARSH',Removable=true,NaturalWonder=false}}
w.feature=3;w.housing=15;w.population=20;w.housingReads=0;w.worker=1;w.surplus=5
local get=c.GetGrowth
c.GetGrowth=function()
 local g=get()
 g.GetHousing=function()
  w.housingReads=w.housingReads+1
  if w.throwHousing then error('housing unavailable')end
  return w.housing
 end
 return g
end
c.GetPopulation=function()return w.population end
''')
        for env,name in [('BAIQI_HOUSING_PLANNER','BaiqiPlanner'),('BAIQI_HOUSING_CONTROLLER','BaiqiController')]:
            override=os.environ.get(env)
            if override:self.lua.execute(Path(override).read_text(encoding='utf-8'))
        self.case.c=self.lua.globals().BaiqiController

    def change(self,s):self.lua.execute(s)

    def compete(self,kind='BUILDING_WORKSHOP',project=False,invested=False,repair=False):
        self.change(r'''
local w=TestWorld;local q=w.objects.city:GetBuildQueue()
q.CanProduce=function(_,hash)return hash==777 or hash==101 or (w.projectAlternative and hash==927)end
GameInfo.Buildings[101].BuildingType='''+repr(kind)+r'''
w.projectAlternative='''+('true'if project else'false')+r'''
if w.projectAlternative then
 local row={Index=2,Hash=927,ProjectType='PROJECT_RETAINED_WORK'}
 GameInfo.Projects=setmetatable({[2]=row,[927]=row,PROJECT_RETAINED_WORK=row},{__call=function()
  local done=false;return function()if not done then done=true;return row end end end})
 q.GetProjectProgress=function()return 143 end;q.GetProjectCost=function()return 170 end
 q.GetBuildingProgress=function(_,i)return i==1 and '''+('73'if invested else'0')+r''' or 0 end
 q.GetBuildingCost=function()return 165 end
end
w.objects.city.GetBuildings=function()return {IsPillaged=function(_,i)return '''+('i==1'if repair else'false')+r''' end}end
CityManager.CanStartOperation=function(city,op,params)
 assert(city==w.objects.city and op==CityOperationTypes.BUILD)
 assert(params[3]==777 or params[2]==101 or (w.projectAlternative and params[5]==927))
 w.eligibilityChecks=w.eligibilityChecks+1;return not w.noCommand
end
''')

    def selected(self):
        self.case.c.RunNow();self.assertEqual(len(self.w.cityRequests),1)
        self.assertEqual(len(self.w.unitRequests),0)
        p=self.w.cityRequests[1]
        return p[2]or p[3]or p[5]

    def test_pure_feature_requires_named_removable_known_deficit_and_accepts_fractional_housing(self):
        f=self.lua.globals().BaiqiPlanner.NeighborhoodFeatureAllowed
        for feature in ['FEATURE_FOREST','FEATURE_JUNGLE']:
            self.assertTrue(f(feature,True,False,15.5,20))
        for args in [('FEATURE_FOREST',True,False,20,20),('FEATURE_FOREST',True,False,21,20),
                     ('FEATURE_FOREST',True,False,-1,20),('FEATURE_FOREST',True,False,None,20),
                     ('FEATURE_FOREST',True,False,15,float('inf')),('FEATURE_FOREST',True,False,15,0),
                     ('FEATURE_FOREST',None,False,15,20),('FEATURE_FOREST',True,None,15,20),
                     ('FEATURE_FOREST',False,False,15,20),('FEATURE_JUNGLE',True,True,15,20),
                     ('FEATURE_FLOODPLAINS',True,False,15,20),(3,True,False,15,20),
                     ('FEATURE_FOREST',True,False,float('nan'),20),('FEATURE_FOREST',True,False,'15',20)]:
            with self.subTest(args=args):self.assertFalse(f(*args))

    def test_pure_score_is_finite_deficit_hint_and_preserves_higher_base(self):
        f=self.lua.globals().BaiqiPlanner.HousingProductionScore
        self.assertEqual(f(55,15.5,20),93);self.assertEqual(f(95,15,20),95)
        for args in [(55,20,20),(55,21,20),(55,None,20),(55,-1,20),(55,15,0),
                     (55,float('nan'),20),(55,15,float('inf')),(55,True,20)]:
            with self.subTest(args=args):self.assertEqual(f(*args),55)
        self.assertEqual(f('unknown',15,20),'unknown')

    def test_actual_forest_jungle_and_fractional_housing_produce_original_district_request(self):
        for feature,housing in [(3,15),(2,19),(3,15.5)]:
            with self.subTest(feature=feature,housing=housing):
                self.setUp();self.w.feature=feature;self.w.housing=housing
                self.case.run_city(1);self.assertEqual(self.w.workReads,2)

    def test_no_actual_deficit_or_unknown_growth_never_uses_forest_exception(self):
        for code in ['w.housing=20','w.housing=21','w.housing=nil','w.housing=-1',
                     'w.housing=0/0','w.population=0','w.population=math.huge','w.throwHousing=true']:
            with self.subTest(code=code):
                self.setUp();self.change('local w=TestWorld;'+code);self.case.run_city(0)

    def test_feature_metadata_rejections_and_other_districts_do_not_widen(self):
        for code in ['w.feature=0','GameInfo.Features[3].Removable=false',
                     'GameInfo.Features[3].NaturalWonder=true','GameInfo.Features[3].NaturalWonder=nil',
                     'GameInfo.Features[3].Index=2','GameInfo.Features[3]=nil',
                     "GameInfo.Features[3].FeatureType='FEATURE_MARSH'",
                     "GameInfo.Districts[777].DistrictType='DISTRICT_CAMPUS'"]:
            with self.subTest(code=code):
                self.setUp();self.change('local w=TestWorld;'+code);self.case.run_city(0)

    def test_new_optional_metadata_throw_does_not_halt_the_controller_and_later_can_recover(self):
        self.change("GameInfo.Features[3].Removable=nil;setmetatable(GameInfo.Features[3],{__index=function(_,k)if k=='Removable'then error('native metadata unavailable')end end})")
        self.case.run_city(0)
        self.assertNotIn('脚本错误',self.case.c.GetStatus())
        self.change('setmetatable(GameInfo.Features[3],nil);GameInfo.Features[3].Removable=true;TestWorld.turn=2')
        self.case.c.RefreshProduction();self.case.run_city(1)

    def test_food_assets_and_original_native_production_gates_stay_required(self):
        for code in ['w.surplus=0','w.worker=nil','w.park=true','w.resource=8',
                     'w.wonder=true','w.isCity=true','w.owner=8','w.hidden=true',
                     'w.noPlacement=true','w.noCommand=true',
                     "GameInfo.Improvements[9].ImprovementType='IMPROVEMENT_FORT'",
                     'local q=w.objects.city:GetBuildQueue();q.CanProduce=function(_,h,m)return h==777 and m~=false end',
                     'local q=w.objects.city:GetBuildQueue();q.CanProduce=function(_,h,m)return h==777 and m~=true end']:
            with self.subTest(code=code):
                self.setUp();self.change('local w=TestWorld;'+code);self.case.run_city(0)

    def test_final_deficit_feature_and_asset_changes_block_dispatch(self):
        for code in ['w.housing=20','w.housing=nil','w.feature=0',
                     'GameInfo.Features[3].Removable=false','GameInfo.Features[3].NaturalWonder=nil',
                     'w.surplus=0','w.resource=8','w.owner=8','w.queueSize=2','w.turn=2']:
            with self.subTest(code=code):
                self.setUp();self.change('TestWorld.shock=function()local w=TestWorld;'+code+' end')
                self.case.run_city(0);self.assertEqual(self.w.eligibilityChecks,2)

    def test_active_queue_is_untouched_without_any_new_housing_or_work_reads(self):
        self.w.queueSize=2;self.case.run_city(0)
        self.assertEqual(self.w.housingReads,0);self.assertEqual(self.w.workReads,0)
        self.assertEqual(self.w.eligibilityChecks,0)

    def test_featureless_ground_and_existing_repair_do_not_require_the_optional_exception(self):
        self.w.feature=-1;self.w.housing=None;self.case.run_city(1)
        self.setUp();self.w.repair=True;self.w.housing=None;self.case.run_city(1)
        self.assertEqual(self.w.housingReads,0);self.assertIsNone(self.w.cityRequests[1][8])

    def test_dam_floodplains_keep_the_original_exception_without_housing_data(self):
        self.change("GameInfo.Features[0]={Index=0,FeatureType='FEATURE_FLOODPLAINS',Removable=false,NaturalWonder=false};GameInfo.Districts[777].DistrictType='DISTRICT_DAM';TestWorld.feature=0;TestWorld.housing=nil")
        self.case.run_city(1);self.assertEqual(self.w.housingReads,0)

    def test_housing_deficit_beats_optional_building_and_retained_project(self):
        self.compete(project=True);self.assertEqual(self.selected(),777)
        self.setUp();self.w.feature=-1;self.w.housing=20;self.compete()
        self.assertEqual(self.selected(),101)

    def test_essential_buildings_and_repairs_stay_ahead_of_new_housing(self):
        for kind,repair in [('BUILDING_GRANARY',False),('BUILDING_MONUMENT',False),
                            ('BUILDING_WATER_MILL',False),('BUILDING_WORKSHOP',True)]:
            with self.subTest(kind=kind,repair=repair):
                self.setUp();self.compete(kind=kind,repair=repair)
                self.assertEqual(self.selected(),101)

    def test_existing_building_investment_keeps_equal_priority_before_housing(self):
        self.compete(project=True,invested=True);self.assertEqual(self.selected(),101)

if __name__=='__main__':unittest.main()
