"""Required dam terrain through the real city planner and final request boundary."""
import unittest
import test_baiqi_district_improvements as districts


class DamFeatureTests(unittest.TestCase):
    def setUp(self):
        self.case = districts.DistrictImprovementTests(methodName='runTest')
        self.case.setUp()
        self.case.lua.execute('''
local w=TestWorld
GameInfo.Districts[777].DistrictType='DISTRICT_DAM'
GameInfo.Features={
 [0]={Index=0,FeatureType='FEATURE_FLOODPLAINS'},
 [1]={Index=1,FeatureType='FEATURE_FLOODPLAINS_GRASSLAND'},
 [2]={Index=2,FeatureType='FEATURE_FLOODPLAINS_PLAINS'}}
w.feature=0
''')

    def change(self, code):
        self.case.lua.execute(code)

    def test_each_required_floodplain_allows_normal_dam_request_over_farm(self):
        for index in (0, 1, 2):
            with self.subTest(index=index):
                self.setUp()
                self.case.w.feature = index
                self.case.run_city(1)
                self.assertEqual(self.case.w.eligibilityChecks, 2)

    def test_other_districts_cannot_use_the_dam_feature_exception(self):
        for kind in ('DISTRICT_ENTERTAINMENT_COMPLEX', 'DISTRICT_HOLY_SITE', 'UNKNOWN'):
            for index in (0, 1, 2):
                with self.subTest(kind=kind, index=index):
                    self.setUp()
                    self.change("GameInfo.Districts[777].DistrictType='" + kind + "'")
                    self.case.w.feature = index
                    self.case.run_city(0)

    def test_invalid_feature_indices_reject_even_with_matching_fake_metadata(self):
        for value in ('0.5', '-2', 'math.huge', '-math.huge', '0/0', "'0'", 'nil'):
            with self.subTest(value=value):
                self.setUp()
                self.change('''
local value=''' + value + '''
TestWorld.feature=value
GameInfo.Features=setmetatable({}, {__index=function()
 return {Index=value,FeatureType='FEATURE_FLOODPLAINS'} end})
''')
                self.case.run_city(0)

    def test_missing_malformed_or_unapproved_feature_definitions_reject(self):
        for code in ('GameInfo.Features=nil', 'GameInfo.Features[0]=nil',
                     'GameInfo.Features[0]=false', 'GameInfo.Features[0]=true',
                     'GameInfo.Features[0]=7', "GameInfo.Features[0]='x'",
                     'GameInfo.Features[0].Index=1', 'GameInfo.Features[0].Index=nil',
                     "GameInfo.Features[0].FeatureType='FEATURE_FOREST'",
                     'GameInfo.Features[0].FeatureType=nil'):
            with self.subTest(code=code):
                self.setUp(); self.change(code); self.case.run_city(0)

    def test_resources_and_other_protected_assets_remain_protected(self):
        for code in ('TestWorld.park=true', 'TestWorld.wonder=true',
                     'TestWorld.isCity=true', 'TestWorld.district=2',
                     'TestWorld.resource=8', 'TestWorld.hidden=true', 'TestWorld.owner=8',
                     "GameInfo.Improvements[9].ImprovementType='IMPROVEMENT_FORT'",
                     'GameInfo.Improvements[9]=nil'):
            with self.subTest(code=code):
                self.setUp(); self.change(code); self.case.run_city(0)

    def test_native_production_placement_and_operation_gates_still_apply(self):
        for gate in ('first', 'second', 'placement', 'operation'):
            with self.subTest(gate=gate):
                self.setUp()
                if gate in ('first', 'second'):
                    self.change('''
local q=TestWorld.objects.city:GetBuildQueue();local old=q.CanProduce
q.CanProduce=function(self,hash,mode,...)
 if hash==777 and mode==''' + ('true' if gate == 'first' else 'false') + ''' then return false end
 return old(self,hash,mode,...) end
''')
                else:
                    self.case.w['noPlacement' if gate == 'placement' else 'noCommand'] = True
                self.case.run_city(0)

    def test_final_feature_asset_and_native_changes_prevent_actual_write(self):
        for code in ("GameInfo.Features[0].FeatureType='FEATURE_FOREST'",
                     'GameInfo.Features[0]=nil', 'GameInfo.Features[0].Index=2',
                     "GameInfo.Districts[777].DistrictType='DISTRICT_ENTERTAINMENT_COMPLEX'",
                     'w.feature=0.5', 'w.park=true', 'w.resource=8',
                     'w.owner=8', 'w.noPlacement=true', 'w.alias=true'):
            with self.subTest(code=code):
                self.setUp()
                self.change('TestWorld.shock=function()local w=TestWorld;' + code + ' end')
                self.case.run_city(0)
                self.assertEqual(self.case.w.eligibilityChecks, 2)

    def test_existing_production_is_preserved_before_qualification(self):
        self.case.w.queueSize = 2
        self.case.run_city(0)
        self.assertEqual(self.case.w.eligibilityChecks, 0)

    def test_repair_and_featureless_native_legal_ground_keep_existing_behavior(self):
        self.case.w.repair = True
        self.change("GameInfo.Features[0].FeatureType='FEATURE_FOREST'")
        self.case.run_city(1)
        self.setUp()
        self.case.w.feature = -1
        self.change('GameInfo.Features=nil')
        self.case.run_city(1)


if __name__ == '__main__':
    unittest.main()
