"""Exercise actual city selection/dispatch over economic improvements in Lua 5.1."""
from pathlib import Path
import unittest
from lupa.lua51 import LuaRuntime

ROOT = Path(__file__).resolve().parents[1]


class DistrictImprovementTests(unittest.TestCase):
    def setUp(self):
        self.lua = LuaRuntime(unpack_returned_tuples=True)
        self.lua.execute((ROOT / 'tests/lua/mock_world.lua').read_text(encoding='utf-8'))
        self.lua.execute('''
local w=TestWorld;local p=Map.GetPlot(2,3);w.plot=p;w.improvement=9;w.feature=-1
YieldTypes.FOOD=1
function p:GetYield(kind)assert(kind==YieldTypes.FOOD);return 0 end
local r={Hash=777,Index=3,DistrictType='DISTRICT_HOLY_SITE'}
GameInfo.Districts=setmetatable({[777]=r,[3]=r},{__call=function()
 local done=false;return function()if not done then done=true;return r end end end})
GameInfo.Improvements[9]={ImprovementType='IMPROVEMENT_FARM'}
GameInfo.Resources[8]={Hash=88}
function p:GetImprovementType()assert(self==p);return w.improvement end
function p:GetFeatureType()return w.feature end
function p:IsCity()return w.isCity==true end
function p:IsNaturalWonder()return w.wonder==true end
function p:IsNationalPark()return w.park==true end
function p:GetDistrictType()return w.district or -1 end
function p:GetResourceType()return w.resource or -1 end
function p:GetOwner()return w.owner or 7 end
function p:CanHaveDistrict(index,owner,city)
 assert(self==p and index==3 and owner==7 and city==66)
 return not w.noPlacement
end
local q=w.objects.city:GetBuildQueue()
function q:HasBeenPlaced(hash)assert(self==q and hash==777);return w.repair==true end
function q:CanProduce(hash)return hash==777 and not w.noProduction end
Map.GetCityPlots=function()return {GetPurchasedPlots=function()return {42}end}end
local resources={}
resources.IsResourceVisible=function(self,h)assert(self==resources and h==88);return true end
w.objects.player.GetResources=function()return resources end
PlayersVisibility[7].IsRevealed=function()return not w.hidden end
local original=Map.GetPlot
Map.GetPlot=function(x,y)
 if w.alias then return {GetX=function()return 99 end,GetY=function()return 99 end}end
 return original(x,y)
end
w.eligibilityChecks=0
CityManager.CanStartOperation=function(city,op,params)
 assert(city==w.objects.city and params[CityOperationTypes.PARAM_DISTRICT_TYPE]==777)
 w.eligibilityChecks=w.eligibilityChecks+1
 if w.eligibilityChecks==2 and w.shock then w.shock()end
 return not w.noCommand
end
''')
        for name in ('BaiqiConfig', 'BaiqiPolicy', 'BaiqiPlanner', 'BaiqiController'):
            self.lua.execute((ROOT / f'mod/Baiqi/Lua/{name}.lua').read_text(encoding='utf-8'))
        self.w = self.lua.globals().TestWorld
        self.c = self.lua.globals().BaiqiController

    def run_city(self, expected):
        self.c.RunNow()
        self.assertEqual(len(self.w.cityRequests), expected)
        self.assertEqual(len(self.w.unitRequests), 0)
        if expected:
            params = self.w.cityRequests[1]
            self.assertEqual(params[3], 777)
            if not self.w.repair:
                self.assertEqual((params[8], params[9]), (2, 3))

    def test_real_prefixed_economic_types_can_be_replaced(self):
        for kind in ('FARM', 'MINE', 'QUARRY', 'PLANTATION', 'PASTURE', 'CAMP', 'LUMBER_MILL'):
            with self.subTest(kind=kind):
                self.setUp()
                self.lua.globals().GameInfo.Improvements[9].ImprovementType = 'IMPROVEMENT_' + kind
                self.run_city(1)

    def test_unimproved_ground_stays_eligible_without_improvement_metadata(self):
        self.w.improvement = -1
        self.lua.execute('GameInfo.Improvements=nil')
        self.run_city(1)

    def test_military_unknown_and_missing_improvements_stay_protected(self):
        for kind in ('FORT', 'MISSILE_SILO', 'GREAT_WALL', 'UNKNOWN', ''):
            with self.subTest(kind=kind):
                self.setUp()
                self.lua.globals().GameInfo.Improvements[9].ImprovementType = 'IMPROVEMENT_' + kind
                self.run_city(0)
        self.setUp()
        self.lua.execute('GameInfo.Improvements[9]=nil')
        self.run_city(0)
        self.setUp()
        self.lua.execute('GameInfo.Improvements=nil')
        self.run_city(0)

    def test_protected_terrain_and_revealed_resource_are_not_consumed(self):
        for key, value in (('park', True), ('wonder', True), ('isCity', True),
                           ('feature', 2), ('district', 2), ('resource', 8), ('hidden', True)):
            with self.subTest(key=key):
                self.setUp()
                self.w[key] = value
                self.run_city(0)

    def test_native_placement_production_and_command_rejections_still_block(self):
        for key in ('noPlacement', 'noProduction', 'noCommand'):
            with self.subTest(key=key):
                self.setUp()
                self.w[key] = True
                self.run_city(0)

    def test_existing_queue_is_not_overwritten(self):
        self.w.queueSize = 2
        self.run_city(0)
        self.assertEqual(self.w.eligibilityChecks, 0)

    def test_farm_becomes_military_improvement_during_final_native_validation(self):
        self.lua.execute("TestWorld.shock=function()GameInfo.Improvements[9].ImprovementType='IMPROVEMENT_FORT'end")
        self.run_city(0)
        self.assertEqual(self.w.eligibilityChecks, 2)

    def test_protection_changes_after_selection_prevent_actual_dispatch(self):
        for change in ('w.park=true', 'w.resource=8', 'w.feature=2', 'w.owner=8',
                       'w.alias=true', 'w.noPlacement=true', 'GameInfo.Districts[777]=nil'):
            with self.subTest(change=change):
                self.setUp()
                self.w.improvement = -1
                self.lua.execute('TestWorld.shock=function()local w=TestWorld;' + change + ' end')
                self.run_city(0)
                self.assertEqual(self.w.eligibilityChecks, 2)

    def test_repair_does_not_require_consuming_a_new_placement(self):
        self.w.repair = True
        self.lua.globals().GameInfo.Improvements[9].ImprovementType = 'IMPROVEMENT_FORT'
        self.run_city(1)
        self.assertIsNone(self.w.cityRequests[1][8])


if __name__ == '__main__':
    unittest.main()
