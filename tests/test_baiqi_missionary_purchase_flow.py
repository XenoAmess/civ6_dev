import unittest
from missionary_purchase_flow_harness import make,R,K


class MissionaryPurchaseFlowTests(unittest.TestCase):
    def setUp(self):
        self.lua,self.logs=make()
        self.g=self.lua.globals();self.w=self.g.TestWorld
        self.h=self.g.TestRelBridge;self.c=self.g.BaiqiController

    def tearDown(self):
        self.assertFalse(any('|error|'in line for line in self.logs),self.logs)

    def op(self):
        return self.h.store[K].operations['1']

    def reload_controller(self):
        self.c.Shutdown()
        self.lua.execute((R/'mod/Baiqi/Lua/BaiqiController.lua').read_text(encoding='utf-8'))
        self.c=self.g.BaiqiController

    def test_one_actual_consumer_purchase_has_persisted_permission_and_exact_receipt(self):
        self.w.autoPurchase=True
        self.c.RunNow();self.c.RunNow()
        self.assertEqual((len(self.w.purchases),self.w.faith,self.op().stage,self.op().newUnitID),(1,100,'OBSERVED',900))
        self.assertEqual(len(self.w.unitRequests),0)
        self.assertEqual(self.h.store['BAIQI_RELIGIOUS_INTENTS_V1'].serial,0)

    def test_unknown_command_result_survives_ui_reload_without_replay(self):
        self.w.throwPurchase=True
        self.c.RunNow()
        self.assertEqual((len(self.w.purchases),self.op().stage),(1,'ARMED'))
        self.reload_controller()
        for _ in range(3):
            self.w.turn+=1;self.c.RunNow()
        self.assertEqual((len(self.w.purchases),self.w.faith,self.op().stage),(1,175,'ARMED'))

    def test_effect_then_throw_can_be_observed_without_repeating_command(self):
        self.w.autoPurchase=True;self.w.throwPurchase=True
        self.c.RunNow();self.c.RunNow()
        self.assertEqual((len(self.w.purchases),self.op().stage,self.w.faith),(1,'OBSERVED',100))

    def test_wrong_debit_holds_new_actor_until_exact_receipt_then_allows_its_order(self):
        self.lua.execute('''
          local old=CityManager.RequestCommand
          CityManager.RequestCommand=function(...)
            old(...);TestWorld.faith=101;TestWorld.missionaryMoves=4
          end
        ''')
        self.w.autoPurchase=True
        self.c.RunNow();self.c.RunNow()
        self.assertEqual((self.op().stage,len(self.w.unitRequests),len(self.w.spreadRequests)),('ARMED',0,0))
        self.w.faith=100
        self.c.RunNow()
        self.assertEqual(self.op().stage,'OBSERVED')
        self.assertTrue(len(self.w.unitRequests)>0 or len(self.w.spreadRequests)>0,self.logs)
        self.assertTrue(all(row.unit==900 for row in self.w.unitRequests.values()))

    def test_unresolved_purchase_does_not_block_unrelated_production(self):
        self.c.RunNow()
        self.assertEqual(self.op().stage,'ARMED')
        self.w.queueSize=0;self.c.RefreshProduction();self.c.RunNow()
        self.assertEqual((len(self.w.purchases),len(self.w.cityRequests)),(1,1))
        self.assertEqual(self.op().stage,'ARMED')

    def test_failed_permission_write_never_buys(self):
        self.h.allowWrite=False;self.c.RunNow()
        self.assertEqual(len(self.w.purchases),0)
        self.assertIsNone(self.h.store[K])

    def test_corrupt_purchase_property_is_preserved(self):
        self.h.store[K]='unknown-old-value'
        self.c.RunNow();self.w.turn+=1;self.c.RunNow()
        self.assertEqual((self.h.store[K],len(self.w.purchases)),('unknown-old-value',0))

    def test_no_created_religion_or_domestic_need_never_buys(self):
        for setup in ('TestWorld.ownReligion=-1','TestWorld.secondCityMajority=1'):
            with self.subTest(setup=setup):
                self.setUp();self.lua.execute(setup);self.c.RunNow()
                self.assertEqual(len(self.w.purchases),0);self.assertIsNone(self.h.store[K])

    def test_no_native_qualification_or_reserve_never_buys(self):
        for field,value in [('purchaseLegal',False),('faith',174)]:
            with self.subTest(field=field):
                self.setUp();self.w[field]=value
                self.c.RunNow();self.c.RunNow();self.c.RunNow()
                self.assertEqual(len(self.w.purchases),0);self.assertIsNone(self.h.store[K])

    def test_hidden_or_foreign_source_and_target_never_buy(self):
        for field,value in [('visible',False),('revealed',False),('plotOwner',8),('cityOwner',8)]:
            with self.subTest(field=field):
                self.setUp();self.w[field]=value
                self.c.RunNow();self.c.RunNow()
                self.assertEqual(len(self.w.purchases),0);self.assertIsNone(self.h.store[K])

    def test_existing_same_faith_immobile_or_escorted_missionary_counts_as_stock(self):
        for formation in (1,2):
            with self.subTest(formation=formation):
                self.setUp();self.w.withMissionary=True;self.w.missionaryMoves=0;self.w.missionaryFormation=formation
                self.c.RunNow()
                self.assertEqual((len(self.w.purchases),len(self.w.unitRequests),len(self.w.spreadRequests)),(0,0,0))

    def test_religious_combat_actors_receive_no_background_orders(self):
        for kind in (61,62,63):
            with self.subTest(kind=kind):
                self.setUp();self.w.withMissionary=True;self.w.missionaryType=kind
                self.c.RunNow();self.c.RunNow()
                self.assertEqual((len(self.w.unitRequests),len(self.w.spreadRequests)),(0,0))
                if self.h.store[K]:
                    self.assertEqual(self.op().unitType,'UNIT_MISSIONARY')

    def test_price_context_or_bridge_change_after_permission_holds_without_command(self):
        for change in ('TestWorld.purchaseCost=76',"PlayerConfigurations[7].GetLeaderTypeName=function()return 'LEADER_OTHER'end",
                       'TestWorld.visible=false','ExposedMembers.BaiqiMissionaryPurchaseBridge={version=99}'):
            with self.subTest(change=change):
                self.setUp()
                self.lua.execute('''
                  local bridge=ExposedMembers.BaiqiMissionaryPurchaseBridge;local old=bridge.Prepare
                  bridge.Prepare=function(...)
                    local a,b,c=old(...);if a then '''+change+''' end;return a,b,c
                  end
                ''')
                self.c.RunNow()
                self.assertEqual((len(self.w.purchases),self.op().stage),(0,'ARMED'))

    def test_last_qualification_can_remove_demand_and_prevent_command(self):
        self.lua.execute('TestWorld.qualificationHook=function(n)if n==3 then TestWorld.secondCityMajority=1 end end')
        self.c.RunNow()
        self.assertEqual((len(self.w.purchases),self.op().stage),(0,'ARMED'))

    def test_parameter_or_native_writer_change_after_permission_prevents_command(self):
        for change in ('CityCommandTypes.PARAM_UNIT_TYPE=14','CityManager.RequestCommand=function()error("foreign writer")end'):
            with self.subTest(change=change):
                self.setUp()
                self.lua.execute('''
                  local bridge=ExposedMembers.BaiqiMissionaryPurchaseBridge;local old=bridge.Prepare
                  bridge.Prepare=function(...)
                    local a,b,c=old(...);if a then '''+change+''' end;return a,b,c
                  end
                ''')
                self.c.RunNow()
                self.assertEqual((len(self.w.purchases),self.op().stage),(0,'ARMED'))

    def test_busy_tick_can_reconcile_existing_receipt_without_new_order(self):
        self.c.RunNow();self.assertEqual(self.op().stage,'ARMED')
        self.w.withMissionary=True;self.w.missionaryID=900;self.w.faith=100;self.w.missionaryMoves=4;self.w.busy=True
        self.c.RunNow()
        self.assertEqual((self.op().stage,len(self.w.purchases),len(self.w.unitRequests)),('OBSERVED',1,0))

    def test_cross_turn_actor_and_balance_are_not_a_same_turn_receipt(self):
        self.c.RunNow()
        self.w.turn+=1;self.w.withMissionary=True;self.w.missionaryID=900;self.w.faith=100;self.w.missionaryMoves=4
        self.c.RunNow()
        self.assertEqual((self.op().stage,len(self.w.purchases),len(self.w.unitRequests)),('ARMED',1,0))


if __name__=='__main__':
    unittest.main()
