import unittest
from lupa.lua53 import LuaRuntime
from purchase_ui_harness import ROOT, KEY, install_purchase_bridge


class PurchaseUITests(unittest.TestCase):
    def setUp(self):
        self.lua = LuaRuntime(unpack_returned_tuples=True)
        for name in ('mock_world','mock_missionary','mock_naturalist','mock_naturalist_purchase'):
            self.lua.execute((ROOT / f'tests/lua/{name}.lua').read_text(encoding='utf-8'))
        self.logs = []
        self.lua.globals().print = lambda *args: self.logs.append(' '.join(map(str,args)))
        install_purchase_bridge(self.lua)
        for name in ('BaiqiConfig','BaiqiPolicy','BaiqiPlanner','BaiqiHeritageCandidates',
                     'BaiqiHeritageActions','BaiqiNaturalistPurchase','BaiqiController'):
            self.lua.execute((ROOT / f'mod/Baiqi/Lua/{name}.lua').read_text(encoding='utf-8'))
        self.w = self.lua.globals().TestWorld
        self.h = self.lua.globals().TestPurchaseBridge
        self.c = self.lua.globals().BaiqiController

    def tearDown(self):
        self.assertFalse(any('|error|' in line for line in self.logs), self.logs)

    def op(self):
        return self.h.store[KEY].operations['1']

    def reload(self):
        self.c.Shutdown()
        saved = self.h.Copy(self.h.store)
        install_purchase_bridge(self.lua, saved)
        self.h = self.lua.globals().TestPurchaseBridge
        self.lua.execute((ROOT / 'mod/Baiqi/Lua/BaiqiController.lua').read_text(encoding='utf-8'))
        self.c = self.lua.globals().BaiqiController

    def test_own_armed_token_allows_one_native_purchase_and_real_effect_receipt(self):
        self.w.autoPurchase = True
        self.c.RunNow()
        self.assertEqual((len(self.w.purchaseRequests),self.op().stage,self.w.faith), (1,'ARMED',100), self.logs)
        self.c.RunNow()
        self.assertEqual((self.op().stage,self.op().newUnitID,self.h.store[KEY].serial), ('OBSERVED',900,1), self.logs)
        self.assertEqual(len(self.w.unitRequests), 0)
        self.assertEqual(self.h.writes, 2)

    def test_unknown_native_result_and_cold_reload_never_replay(self):
        self.w.throwPurchase = True
        self.c.RunNow()
        self.assertEqual((len(self.w.purchaseRequests),self.op().stage), (1,'ARMED'))
        self.reload()
        for _ in range(3):
            self.w.turn += 1
            self.c.RunNow()
        self.assertEqual((len(self.w.purchaseRequests),self.op().stage,self.w.faith), (1,'ARMED',400), self.logs)

    def test_unconfirmed_permission_does_not_buy_or_stop_production(self):
        self.h.allowWrite = False
        self.c.RunNow()
        self.assertEqual(len(self.w.purchaseRequests), 0, self.logs)
        self.w.queueSize = 0
        self.c.RefreshProduction()
        self.c.RunNow()
        self.assertEqual(len(self.w.cityRequests), 1, self.logs)

    def test_quote_change_after_grant_holds_without_dispatch(self):
        self.lua.execute('''
          TestWorld.onPurchaseQualification=function(count)
            if count==2 then TestWorld.purchaseCost=301 end
          end
        ''')
        self.c.RunNow()
        self.assertEqual((len(self.w.purchaseRequests),self.op().stage), (0,'ARMED'), self.logs)
        self.w.purchaseCost = 300
        self.reload()
        self.w.turn += 1
        self.c.RunNow()
        self.assertEqual((len(self.w.purchaseRequests),self.op().stage), (0,'ARMED'))

    def test_parameter_key_change_after_grant_is_not_new_permission(self):
        self.lua.execute('''
          local bridge=ExposedMembers.BaiqiNaturalistPurchaseBridge
          local prepare=bridge.Prepare
          bridge.Prepare=function(...)
            local granted,token,reason=prepare(...)
            if granted then CityCommandTypes.PARAM_UNIT_TYPE=-1234 end
            return granted,token,reason
          end
        ''')
        self.c.RunNow()
        self.assertEqual((len(self.w.purchaseRequests),self.op().stage), (0,'ARMED'), self.logs)

    def test_demand_lost_after_last_native_qualification_prevents_dispatch(self):
        self.lua.execute('''
          TestWorld.onPurchaseQualification=function(count)
            if count==2 then TestWorld.parkCandidates={} end
          end
        ''')
        self.c.RunNow()
        self.assertEqual((len(self.w.purchaseRequests),self.op().stage), (0,'ARMED'), self.logs)

    def test_unsafe_hidden_foreign_or_unwalkable_demand_never_arms(self):
        for field,value in (('visible',False),('plotOwner',8),('waterTarget',True),('impassableTarget',True)):
            with self.subTest(field=field):
                self.setUp()
                self.w[field] = value
                self.c.RunNow()
                self.assertEqual(len(self.w.purchaseRequests), 0, self.logs)
                self.assertIsNone(self.h.store[KEY])

    def test_existing_live_naturalist_or_escort_stops_new_purchase(self):
        for formation in (1,2):
            with self.subTest(formation=formation):
                self.setUp()
                self.w.withMissionary = True
                self.w.missionaryFormation = formation
                self.w.missionaryMoves = 0
                self.c.RunNow()
                self.assertEqual(len(self.w.purchaseRequests), 0, self.logs)
                self.assertIsNone(self.h.store[KEY])
                self.assertEqual(len(self.w.unitRequests), 0)

    def test_price_unaffordable_or_native_rejected_never_arms(self):
        for field,value in (('faith',399),('purchaseLegal',False)):
            with self.subTest(field=field):
                self.setUp()
                self.w[field] = value
                self.c.RunNow()
                self.assertEqual(len(self.w.purchaseRequests), 0, self.logs)
                self.assertIsNone(self.h.store[KEY])

    def test_busy_tick_can_read_effect_without_new_orders(self):
        self.w.autoPurchase = True
        self.c.RunNow()
        self.w.busy = True
        self.c.RunNow()
        self.assertEqual((self.op().stage,len(self.w.purchaseRequests)), ('OBSERVED',1), self.logs)
        self.assertEqual(len(self.w.unitRequests), 0)


if __name__ == '__main__':
    unittest.main()
