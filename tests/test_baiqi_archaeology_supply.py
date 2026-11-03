import unittest
import test_baiqi_archaeology_ui as ui_tests


class ArchaeologySupplyTests(unittest.TestCase):
    def setUp(self):
        self.case = ui_tests.ArchaeologyUITests()
        self.case.setUp()
        self.lua, self.w, self.c, self.logs = self.case.lua, self.case.w, self.case.c, self.case.logs
        self.lua.execute('''
          local W=TestWorld
          W.withMissionary=false;W.queueSize=0
          local row=GameInfo.Units[60];row.Hash=600;row.Index=60;row.Maintenance=0
          GameInfo.Units[600]=row
          setmetatable(GameInfo.Units,{__call=function() local done=false;return function()
            if not done then done=true;return row end end end})
          W.objects.city:GetBuildQueue().CanProduce=function(_,hash) return hash==600 end
          W.objects.player.GetTreasury=function() return {
            GetGoldBalance=function() return W.gold or 1000 end,GetGoldYield=function() return 30 end,
            GetTotalMaintenance=function() return 0 end} end
          Map.GetCityPlots=function() return {GetPurchasedPlots=function() return {42} end} end
          local plot=Map.GetPlotByIndex(42);local resource=plot.GetResourceType
          W.supplyResourceReads=0
          plot.GetResourceType=function(self) W.supplyResourceReads=W.supplyResourceReads+1;return resource(self) end
          local native=CityManager.CanStartOperation
          W.cityQualifications=0
          CityManager.CanStartOperation=function(city,operation,params,...)
            if params[CityOperationTypes.PARAM_UNIT_TYPE]==600 then
              W.cityQualifications=W.cityQualifications+1
              if W.onSupplyQualification then W.onSupplyQualification(W.cityQualifications) end
            end
            return native(city,operation,params,...)
          end
        ''')

    def tearDown(self):
        self.case.tearDown()

    def test_existing_city_writer_recruits_eligible_archaeologist_without_ordering_army(self):
        self.c.RunNow()
        self.assertEqual((len(self.w.cityRequests), len(self.w.unitRequests)), (1, 0), self.logs)
        self.assertEqual(self.w.cityRequests[1][4], 600)
        self.assertGreaterEqual(self.w.supplyResourceReads, 2)

    def test_assigned_or_unknown_home_holds_supply_other_home_can_recruit(self):
        for home, expected in ((66, 0), (-1, 0), (67, 1)):
            with self.subTest(home=home):
                self.setUp()
                self.w.withMissionary, self.w.archHome = True, home
                self.c.RunNow()
                self.assertEqual(len(self.w.cityRequests), expected, self.logs)

    def test_intact_museum_empty_capacity_is_required(self):
        for mutation in ('TestWorld.archSlots={101,102,103}', 'TestWorld.archPillaged=true',
                         'TestWorld.archMuseum=false', 'TestWorld.objects.city:GetBuildings().GetNumGreatWorkSlots=nil'):
            with self.subTest(mutation=mutation):
                self.setUp()
                self.lua.execute(mutation)
                self.c.RunNow()
                self.assertEqual(len(self.w.cityRequests), 0, self.logs)

    def test_hidden_resource_is_not_read_for_supply_or_recruited(self):
        self.w.visible = False
        self.c.RunNow()
        self.assertEqual((len(self.w.cityRequests), self.w.supplyResourceReads), (0, 0), self.logs)

    def test_supply_change_after_last_native_city_qualification_blocks_request(self):
        for mutation in ('TestWorld.archSlots={101,102,103}',
                         'TestWorld.withMissionary=true;TestWorld.archHome=66',
                         'TestWorld.visible=false'):
            with self.subTest(mutation=mutation):
                self.setUp()
                self.lua.execute('TestWorld.onSupplyQualification=function(n) if n==2 then ' + mutation + ' end end')
                self.c.RunNow()
                self.assertEqual((len(self.w.cityRequests), self.w.cityQualifications), (0, 2), self.logs)

    def test_existing_economy_reserve_gate_applies_to_archaeologist(self):
        self.w.gold = 0
        self.c.RunNow()
        self.assertEqual(len(self.w.cityRequests), 0, self.logs)


if __name__ == '__main__':
    unittest.main()
