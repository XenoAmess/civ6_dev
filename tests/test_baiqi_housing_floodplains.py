"""Native-shaped city dispatch on lawful floodplains, with original protections."""
from pathlib import Path
import sys,unittest
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT));sys.path.insert(0,str(ROOT/'tests'))
import test_baiqi_housing_placement as housing

class HousingFloodplainTests(unittest.TestCase):
    def setUp(self):
        self.base=housing.HousingPlacementTests(methodName='runTest');self.base.setUp()
        self.case=self.base.case;self.lua=self.base.lua;self.w=self.base.w
        self.lua.execute('''
GameInfo.Features[0]={Index=0,FeatureType='FEATURE_FLOODPLAINS',Removable=false,NaturalWonder=false}
GameInfo.Features[31]={Index=31,FeatureType='FEATURE_FLOODPLAINS_GRASSLAND',Removable=false,NaturalWonder=false}
GameInfo.Features[32]={Index=32,FeatureType='FEATURE_FLOODPLAINS_PLAINS',Removable=false,NaturalWonder=false}
TestWorld.feature=0;TestWorld.housing=19;TestWorld.population=20
TestWorld.placementFood=6;TestWorld.surplus=25;TestWorld.worker=1
''')

    def change(self,s):self.lua.execute(s)

    def test_actual_beijing_shaped_food_six_and_known_deficit_uses_only_original_build(self):
        self.case.run_city(1);self.assertEqual(self.w.workReads,2)
        self.assertEqual(self.w.cityRequests[1][3],777)
        self.assertEqual((self.w.cityRequests[1][8],self.w.cityRequests[1][9]),(2,3))

    def test_all_three_floodplain_definitions_accept_finite_fractional_housing_shortage(self):
        for feature in [0,31,32]:
            with self.subTest(feature=feature):
                self.setUp();self.w.feature=feature;self.w.housing=19.5
                self.case.run_city(1)

    def test_xian_food_seven_at_net_five_is_rejected_and_explicit_unworked_or_equal_margin_is_allowed(self):
        self.w.feature=31;self.w.placementFood=7;self.w.surplus=5
        self.case.run_city(0)
        self.setUp();self.w.feature=31;self.w.placementFood=7;self.w.surplus=5;self.w.worker=0
        self.case.run_city(1)
        self.setUp();self.w.placementFood=5;self.w.surplus=5;self.case.run_city(1)

    def test_unknown_metadata_natural_wonder_and_nondeficit_never_grant_flood_permission(self):
        for code in ['GameInfo.Features[0].Removable=true','GameInfo.Features[0].Removable=nil',
                     "GameInfo.Features[0].Removable='false'",'GameInfo.Features[0].NaturalWonder=nil',
                     'GameInfo.Features[0].NaturalWonder=true','GameInfo.Features[0].Index=31',
                     "GameInfo.Features[0].FeatureType='FEATURE_MARSH'",'GameInfo.Features[0]=nil',
                     'w.housing=20','w.housing=nil','w.housing=-1','w.housing=0/0',
                     'w.population=0','w.population=math.huge']:
            with self.subTest(code=code):
                self.setUp();self.change('local w=TestWorld;'+code);self.case.run_city(0)

    def test_last_boundary_rechecks_food_deficit_and_definition_and_accepts_still_legal_feature(self):
        for code in ['w.housing=20','w.surplus=0','w.queueSize=2','w.owner=8','w.turn=2',
                     "GameInfo.Features[0].FeatureType='FEATURE_ICE'",'GameInfo.Features[0].Removable=true']:
            with self.subTest(code=code):
                self.setUp();self.change('TestWorld.shock=function()local w=TestWorld;'+code+' end')
                self.case.run_city(0);self.assertEqual(self.w.eligibilityChecks,2)
        self.setUp();self.change('TestWorld.shock=function()TestWorld.feature=3 end');self.case.run_city(1)

    def test_assets_native_production_and_live_operation_still_guard_the_flood_site(self):
        for code in ['w.resource=8','w.park=true','w.wonder=true','w.hidden=true','w.noPlacement=true',
                     'w.noCommand=true',"GameInfo.Improvements[9].ImprovementType='IMPROVEMENT_FORT'",
                     'local q=w.objects.city:GetBuildQueue();q.CanProduce=function(_,h,m)return h==777 and m~=false end',
                     'local q=w.objects.city:GetBuildQueue();q.CanProduce=function(_,h,m)return h==777 and m~=true end']:
            with self.subTest(code=code):
                self.setUp();self.change('local w=TestWorld;'+code);self.case.run_city(0)

    def test_active_queue_avoids_extra_reads_and_dam_branch_keeps_its_own_qualification(self):
        self.w.queueSize=2;self.case.run_city(0)
        self.assertEqual(self.w.housingReads,0);self.assertEqual(self.w.workReads,0)
        self.assertEqual(self.w.eligibilityChecks,0)
        self.setUp();self.change("GameInfo.Districts[777].DistrictType='DISTRICT_DAM';TestWorld.feature=31;TestWorld.housing=nil")
        self.case.run_city(1);self.assertEqual(self.w.housingReads,0)

if __name__=='__main__':unittest.main()
