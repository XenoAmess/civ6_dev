import unittest
import test_baiqi_naturalist_purchase_ui as ui


class PurchaseParkCouplingTests(unittest.TestCase):
    setUp = ui.PurchaseUITests.setUp
    tearDown = ui.PurchaseUITests.tearDown
    op = ui.PurchaseUITests.op
    reload = ui.PurchaseUITests.reload

    def load_park_bridge(self):
        load = self.lua.eval('function(source,name,env) local chunk,err=load(source,name,"t",env);assert(chunk,err);return chunk() end')
        for name in ('BaiqiNaturalistJournal', 'BaiqiNaturalistIntentGameplay'):
            load((ui.ROOT / f'mod/Baiqi/Lua/{name}.lua').read_text(encoding='utf-8'), name, self.h.core)
        self.assertEqual(self.lua.eval('ExposedMembers.BaiqiNaturalistIntentBridge.marker'), 'baiqi-naturalist-intent-v1')
        self.assertEqual(self.lua.eval('ExposedMembers.BaiqiNaturalistPurchaseBridge.marker'), 'baiqi-naturalist-purchase-v1')

    def purchase(self, partial):
        self.load_park_bridge()
        self.w.autoPurchase = True
        self.w.partialPurchase = partial
        self.lua.execute('''
          local original=CityManager.RequestCommand
          CityManager.RequestCommand=function(...)
            original(...);TestWorld.missionaryMoves=4
            if TestWorld.partialPurchase then TestWorld.faith=TestWorld.faith+1 end
          end
        ''')
        self.c.RunNow()
        self.assertEqual((len(self.w.purchaseRequests), self.w.missionaryID, self.op().stage), (1, 900, 'ARMED'), self.logs)

    def test_incomplete_payment_holds_unit_until_purchase_receipt(self):
        self.purchase(True)
        self.assertEqual(self.w.faith, 101)
        self.c.RunNow()
        self.assertEqual(self.op().stage, 'ARMED', self.logs)
        self.assertEqual(len(self.w.unitRequests), 0, self.logs)

    def test_complete_payment_observed_before_normal_naturalist_move(self):
        self.purchase(False)
        self.c.RunNow()
        self.assertEqual((len(self.w.purchaseRequests), self.op().stage, self.op().newUnitID), (1, 'OBSERVED', 900), self.logs)
        self.assertEqual(len(self.w.unitRequests), 1, self.logs)
        self.assertEqual((self.w.unitRequests[1].unit, self.w.unitRequests[1].op), (900, 10), self.logs)

    def test_cold_ui_retains_core_hold_and_other_production_continues(self):
        self.purchase(True)
        self.reload()
        self.load_park_bridge()
        self.w.queueSize = 0
        self.c.RefreshProduction()
        for _ in range(3):
            self.c.RunNow()
        self.assertEqual(self.op().stage, 'ARMED', self.logs)
        self.assertEqual(len(self.w.unitRequests), 0, self.logs)
        self.assertEqual(len(self.w.purchaseRequests), 1)
        self.assertEqual(len(self.w.cityRequests), 1, self.logs)


if __name__ == '__main__':
    unittest.main()
