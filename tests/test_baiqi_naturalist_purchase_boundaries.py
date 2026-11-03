import unittest
import test_baiqi_naturalist_purchase_ui as ui


class PurchaseBoundaryTests(unittest.TestCase):
    setUp = ui.PurchaseUITests.setUp
    tearDown = ui.PurchaseUITests.tearDown
    op = ui.PurchaseUITests.op
    reload = ui.PurchaseUITests.reload

    def effect_then_throw(self):
        self.w.autoPurchase = True
        self.lua.execute('''
          local original=CityManager.RequestCommand
          CityManager.RequestCommand=function(...)
            original(...)
            error('native applied purchase before throwing')
          end
        ''')

    def test_effect_then_throw_observes_once_and_reload_never_replays(self):
        self.effect_then_throw()
        self.c.RunNow()
        self.assertEqual((len(self.w.purchaseRequests), self.w.faith, self.op().stage,
                          self.h.writes), (1, 100, 'ARMED', 1), self.logs)
        self.assertIsNone(self.op().newUnitID)
        self.c.RunNow()
        self.assertEqual((self.op().stage, self.op().newUnitID,
                          self.h.store[ui.KEY].serial, self.h.writes),
                         ('OBSERVED', 900, 1, 2), self.logs)
        self.reload()
        self.c.RunNow()
        self.assertEqual((len(self.w.purchaseRequests), self.w.faith,
                          self.op().newUnitID, self.h.writes), (1, 100, 900, 0), self.logs)

    def test_reload_before_readback_reconciles_effect_without_replay(self):
        self.effect_then_throw()
        self.c.RunNow()
        self.assertEqual((self.op().stage, self.h.writes), ('ARMED', 1), self.logs)
        self.reload()
        self.assertEqual((self.op().stage, self.h.writes), ('ARMED', 0), self.logs)
        self.c.RunNow()
        self.assertEqual((self.op().stage, self.op().newUnitID, self.h.writes,
                          len(self.w.purchaseRequests), self.w.faith),
                         ('OBSERVED', 900, 1, 1, 100), self.logs)

    def cities(self, count, eligible_id=None, with_builder=False):
        self.w.extraCityCount = count
        self.w.eligiblePurchaseCity = eligible_id
        self.w.schedulingBuilder = with_builder
        self.lua.execute('''
          local w=TestWorld
          local base=w.objects.city
          base.GetCityAI=function() return nil end
          local originalPlot=Map.GetPlotByIndex
          local prototype=originalPlot(44)
          local cities,plots={},{}
          for i=0,w.extraCityCount-1 do
            local id,x,index=66+i,2+i,42+i
            plots[index]=setmetatable({GetIndex=function() return index end,
              GetX=function() return x end,GetY=function() return 3 end,
              IsImprovementPillaged=function() return false end,
              GetImprovementType=function() return -1 end},{__index=prototype})
            cities[#cities+1]=setmetatable({GetID=function() return id end,
              GetX=function() return x end,GetY=function() return 3 end},{__index=base})
          end
          Map.GetPlotByIndex=function(index) return plots[index] or originalPlot(index) end
          Map.GetPlot=function(x,y) if y==3 then return Map.GetPlotByIndex(x+40) end end
          w.objects.player.GetCities=function()
            return {Members=function() return ipairs(cities) end,GetCount=function() return #cities end,
              FindID=function(_,id) for _,city in ipairs(cities) do if city:GetID()==id then return city end end end}
          end
          local originalUnits=w.objects.player.GetUnits
          w.objects.player.GetUnits=function(...)
            local units=originalUnits(...)
            local list={};for _,unit in units:Members() do list[#list+1]=unit end
            if w.schedulingBuilder then list[#list+1]=w.objects.builder end
            return {Members=function() return ipairs(list) end,
              FindID=function(_,id) for _,unit in ipairs(list) do if unit:GetID()==id then return unit end end end}
          end
          w.qualifiedCities={}
          CityManager.CanStartCommand=function(city,op,visible,params,results)
            assert(op==CityCommandTypes.PURCHASE and visible==false and results==true)
            assert(params[CityCommandTypes.PARAM_UNIT_TYPE]==GameInfo.Units.UNIT_NATURALIST.Hash)
            assert(params[CityCommandTypes.PARAM_YIELD_TYPE]==5 and params[CityCommandTypes.PARAM_MILITARY_FORMATION_TYPE]==0)
            w.purchaseQualifications=w.purchaseQualifications+1
            w.qualifiedCities[#w.qualifiedCities+1]=city:GetID()
            return city:GetID()==w.eligiblePurchaseCity
          end
          CityManager.RequestCommand=function(city,op,params)
            local record=TestPurchaseBridge.store.BAIQI_NATURALIST_PURCHASE_INTENTS_V1.operations['1']
            assert(record.stage=='ARMED' and record.cityID==city:GetID())
            assert(op==CityCommandTypes.PURCHASE and city:GetID()==w.eligiblePurchaseCity)
            assert(params[CityCommandTypes.PARAM_UNIT_TYPE]==GameInfo.Units.UNIT_NATURALIST.Hash)
            w.purchaseRequests[#w.purchaseRequests+1]={city=city:GetID(),op=op,params=params}
          end
        ''')

    def test_denied_earlier_cities_allow_one_later_purchase(self):
        self.cities(6, eligible_id=68)
        counts = []
        for _ in range(4):
            self.c.RunNow()
            counts.append(self.w.purchaseQualifications)
        self.assertEqual(counts, [1, 2, 2, 4], self.logs)
        self.assertEqual((len(self.w.purchaseRequests), self.w.purchaseRequests[1].city,
                          self.op().cityID, self.h.writes), (1, 68, 68, 1), self.logs)
        self.assertEqual(len(self.w.unitRequests), 0)

    def test_denials_yield_to_actual_builder_order_after_two_callbacks(self):
        self.cities(6, with_builder=True)
        counts = []
        for _ in range(3):
            self.c.RunNow()
            counts.append(self.w.purchaseQualifications)
        self.assertEqual(counts, [1, 2, 2], self.logs)
        self.assertEqual(len(self.w.purchaseRequests), 0)
        self.assertIsNone(self.h.store[ui.KEY])
        self.assertEqual(len(self.w.unitRequests), 1, self.logs)
        self.assertEqual((self.w.unitRequests[1].unit, self.w.unitRequests[1].op),
                         (3, self.lua.globals().UnitOperationTypes.SKIP_TURN), self.logs)


if __name__ == '__main__':
    unittest.main()
