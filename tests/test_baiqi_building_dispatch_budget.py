"""Recheck a building's ongoing cost against changes during native validation."""
from pathlib import Path
import unittest
from lupa.lua53 import LuaRuntime

ROOT = Path(__file__).resolve().parents[1]


class BuildingDispatchBudgetTests(unittest.TestCase):
    def setUp(self):
        self.lua = LuaRuntime(unpack_returned_tuples=True)
        self.lua.execute((ROOT / 'tests/lua/mock_world.lua').read_text(encoding='utf-8'))
        self.lua.execute('''
local w=TestWorld
w.income=6;w.maintenance=0;w.pillaged=false;w.eligibilityChecks=0
GameInfo.Buildings[101].Maintenance=2
w.objects.player.GetTreasury=function() return {
 GetGoldBalance=function()return 10 end,
 GetGoldYield=function()return w.income end,
 GetTotalMaintenance=function()return w.maintenance end}end
w.objects.city.GetBuildings=function()return {
 IsPillaged=function(_,index)return index==1 and w.pillaged end}end
CityManager.CanStartOperation=function(_,_,params)
 if params[CityOperationTypes.PARAM_BUILDING_TYPE]==101 then
  w.eligibilityChecks=w.eligibilityChecks+1
  if w.eligibilityChecks==2 and w.shock then w.shock() end
 end
 return true
end
''')
        for name in ('BaiqiConfig', 'BaiqiPolicy', 'BaiqiPlanner', 'BaiqiController'):
            self.lua.execute((ROOT / f'mod/Baiqi/Lua/{name}.lua').read_text(encoding='utf-8'))
        self.w = self.lua.globals().TestWorld
        self.c = self.lua.globals().BaiqiController

    def assert_building_request(self):
        self.assertEqual(len(self.w.cityRequests), 1)
        self.assertEqual(self.w.cityRequests[1][2], 101)
        self.assertEqual(len(self.w.unitRequests), 0)

    def test_affordable_and_exact_minimum_boundary_are_allowed(self):
        for income in (6, 4):
            with self.subTest(income=income):
                self.setUp()
                self.w.income = income
                self.c.RunNow()
                self.assert_building_request()

    def test_income_falls_at_validation_then_same_turn_retry_uses_restored_budget(self):
        self.lua.execute('TestWorld.shock=function()TestWorld.income=1 end')
        self.c.RunNow()
        self.assertEqual(self.w.eligibilityChecks, 2)
        self.assertEqual(len(self.w.cityRequests), 0)
        self.w.income = 6
        self.c.RunNow()
        self.assert_building_request()

    def test_current_maintenance_rises_after_selection(self):
        self.lua.execute('TestWorld.shock=function()TestWorld.maintenance=4 end')
        self.c.RunNow()
        self.assertEqual(len(self.w.cityRequests), 0)
        self.assertEqual(len(self.w.unitRequests), 0)

    def test_candidate_maintenance_is_not_removed_from_initial_budget(self):
        self.w.income = 3
        self.c.RunNow()
        self.assertEqual(len(self.w.cityRequests), 0)
        self.assertEqual(self.w.eligibilityChecks, 0)

    def test_definition_disappears_before_dispatch(self):
        self.lua.execute('TestWorld.shock=function()GameInfo.Buildings[101]=nil end')
        self.c.RunNow()
        self.assertEqual(len(self.w.cityRequests), 0)

    def test_free_building_and_actual_repair_keep_their_exemptions(self):
        for maintenance, pillaged in ((0, False), (5, True)):
            with self.subTest(maintenance=maintenance, pillaged=pillaged):
                self.setUp()
                self.lua.globals().GameInfo.Buildings[101].Maintenance = maintenance
                self.w.pillaged = pillaged
                self.lua.execute('TestWorld.shock=function()TestWorld.income=-5 end')
                self.c.RunNow()
                self.assert_building_request()

    def test_repaired_elsewhere_cannot_keep_stale_repair_exemption(self):
        self.w.pillaged = True
        self.lua.execute('TestWorld.shock=function()TestWorld.income=1;TestWorld.pillaged=false end')
        self.c.RunNow()
        self.assertEqual(len(self.w.cityRequests), 0)

    def test_other_city_queue_commitment_is_refreshed_before_dispatch(self):
        self.lua.execute('''
local w=TestWorld;local main=w.objects.city
local other=setmetatable({GetID=function()return 67 end,
 GetBuildQueue=function()return {
  GetSize=function()return 1 end,
  GetAt=function()return {UnitType=1}end,
  GetCurrentProductionTypeHash=function()return 201 end,
  CanProduce=function()return false end}end},{__index=main})
w.objects.player.GetCities=function()return {
 Members=function()return ipairs({main,other})end,
 GetCount=function()return 2 end,
 FindID=function(_,id)if id==66 then return main elseif id==67 then return other end end}end
w.shock=function()GameInfo.Units[1].Maintenance=4 end
''')
        self.c.RunNow()
        self.assertEqual(self.w.eligibilityChecks, 2)
        self.assertEqual(len(self.w.cityRequests), 0)
        self.assertEqual(len(self.w.unitRequests), 0)


if __name__ == '__main__':
    unittest.main()
