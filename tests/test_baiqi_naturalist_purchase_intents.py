import unittest
from purchase_intent_harness import make_purchase_core, KEY


class PurchaseIntentTests(unittest.TestCase):
    def setUp(self):
        self.lua = make_purchase_core()
        self.h = self.lua.globals().H
        self.s = self.lua.globals().S
        self.bridge = self.lua.globals().ExposedMembers.BaiqiNaturalistPurchaseBridge

    def prepare(self, **changes):
        args = dict(pid=0,cityID=65536,x=16,y=14,unitHash=1877270220,cost=300,faithBefore=400,reserve=100)
        args.update(changes)
        return self.bridge.Prepare(*(args[k] for k in ('pid','cityID','x','y','unitHash','cost','faithBefore','reserve')))

    def op(self):
        return self.h.store[KEY].operations['1']

    def effect(self):
        self.lua.execute('AddPurchasedUnit(6000000);S.faith=100')

    def test_nil_inspection_is_open_and_has_no_property_write(self):
        self.assertEqual(self.bridge.Inspect(0)[0], 'OPEN')
        self.assertEqual(self.h.writes, 0)
        self.assertIsNone(self.h.store[KEY])

    def test_prepare_persists_once_and_confirms_readback(self):
        granted,token,_ = self.prepare()
        self.assertEqual((granted,token,self.h.writes), (True,'purchase:0:1',1))
        self.assertEqual((self.op().stage,self.op().cost,self.op().faithBefore), ('ARMED',300,400))
        self.assertEqual(self.bridge.Inspect(0)[0:2], ('ARMED',token))
        self.assertEqual(self.h.writes, 1)

    def test_unresolved_is_global_and_survives_cold_metadata_reload(self):
        self.assertTrue(self.prepare()[0])
        self.assertFalse(self.prepare(cityID=65537)[0])
        saved = self.h.Copy(self.h.store)
        lua = make_purchase_core(stored=saved)
        bridge = lua.globals().ExposedMembers.BaiqiNaturalistPurchaseBridge
        self.assertEqual(bridge.Inspect(0)[0], 'ARMED')
        self.assertFalse(bridge.Prepare(0,65536,16,14,1877270220,300,400,100)[0])
        self.assertEqual(lua.globals().H.writes, 0)

    def test_actual_new_unit_and_exact_debit_confirm_once(self):
        self.assertTrue(self.prepare()[0])
        self.effect()
        self.assertEqual(self.bridge.Inspect(0,'purchase:0:1')[0:2], ('OBSERVED','purchase:0:1'))
        self.assertEqual((self.op().newUnitID,self.op().faithAfter,self.h.writes), (6000000,100,2))
        self.assertEqual(self.bridge.Inspect(0,'purchase:0:1')[0], 'OBSERVED')
        self.assertEqual(self.h.writes, 2)
        self.assertEqual(self.bridge.Inspect(0)[0], 'OPEN')

    def test_absence_wrong_debit_city_or_turn_are_not_receipts(self):
        for setup in ('S.faith=100','AddPurchasedUnit(6000000)',
                      'AddPurchasedUnit(6000000);S.faith=101',
                      'AddPurchasedUnit(6000000);S.faith=100;H.turn=93',
                      'AddPurchasedUnit(6000000);S.faith=100;S.owner=1',
                      'AddPurchasedUnit(6000000);S.faith=100;H.newUnit.x=17',
                      'AddPurchasedUnit(6000000);S.faith=100;H.newUnit.formation=2'):
            with self.subTest(setup=setup):
                self.setUp()
                self.assertTrue(self.prepare()[0])
                self.lua.execute(setup)
                self.assertEqual(self.bridge.Inspect(0,'purchase:0:1')[0], 'ARMED')
                self.assertEqual((self.op().stage,self.h.writes), ('ARMED',1))

    def test_missing_key_invalid_state_and_failed_read_do_not_reset(self):
        lua = make_purchase_core(inject_key=False)
        bridge = lua.globals().ExposedMembers.BaiqiNaturalistPurchaseBridge
        self.assertEqual(bridge.Inspect(0)[0], 'UNAVAILABLE')
        self.assertFalse(bridge.Prepare(0,65536,16,14,1877270220,300,400,100)[0])
        self.assertEqual((lua.globals().H.reads,lua.globals().H.writes), (0,0))
        self.h.store[KEY] = 'unknown old state'
        self.assertEqual(self.bridge.Inspect(0)[0], 'UNKNOWN')
        self.assertFalse(self.prepare()[0])
        self.assertEqual((self.h.store[KEY],self.h.writes), ('unknown old state',0))
        self.h.throwRead = True
        self.assertEqual(self.bridge.Inspect(0)[0], 'UNAVAILABLE')
        self.assertFalse(self.prepare()[0])
        self.assertEqual(self.h.writes, 0)

    def test_unconfirmed_intent_or_receipt_never_grants_or_clears(self):
        for field in ('allowWrite','throwWrite','corruptWrite'):
            with self.subTest(field=field):
                self.setUp()
                self.h[field] = field != 'allowWrite'
                self.assertFalse(self.prepare()[0])
        self.setUp()
        self.assertTrue(self.prepare()[0])
        self.effect()
        self.h.allowWrite = False
        self.assertEqual(self.bridge.Inspect(0,'purchase:0:1')[0], 'UNKNOWN')
        self.assertEqual(self.op().stage, 'ARMED')
        self.assertFalse(self.prepare()[0])

    def test_owner_mode_stock_budget_and_hash_boundaries(self):
        for setup in ("H.localPlayer=1", "H.human=false", "H.active=false", "H.leader='LEADER_OTHER'",
                      'H.multiplayer=true','H.hotseat=true','S.records[1].dead=false',
                      'S.faith=399','GameInfo.Units[19].Hash=123'):
            with self.subTest(setup=setup):
                self.setUp()
                self.lua.execute(setup)
                self.assertFalse(self.prepare()[0])
                self.assertEqual(self.h.writes, 0)
        self.setUp()
        self.lua.execute('GameInfo.Units[19].Hash=-1000')
        self.assertTrue(self.prepare(unitHash=-1000)[0])

    def test_unknown_token_is_exact_and_inactive_receipts_still_work(self):
        self.assertTrue(self.prepare()[0])
        for token in ('purchase:1:1','prefixpurchase:0:1','purchase:0:01',1):
            self.assertEqual(self.bridge.Inspect(0,token)[0], 'UNKNOWN')
        self.effect()
        self.h.active = False
        self.assertEqual(self.bridge.Inspect(0,'purchase:0:1')[0], 'OBSERVED')

    def test_snapshot_change_or_concurrent_journal_does_not_grant(self):
        self.lua.execute('''
          local original=TestUnits.Members
          local calls=0
          TestUnits.Members=function(...)
            calls=calls+1
            if calls==2 then S.faith=399 end
            return original(...)
          end
        ''')
        self.assertFalse(self.prepare()[0])
        self.assertEqual(self.h.writes, 0)
        self.setUp()
        self.lua.execute('''
          local original=TestUnits.Members
          local calls=0
          TestUnits.Members=function(...)
            calls=calls+1
            if calls==2 then
              H.store.BAIQI_NATURALIST_PURCHASE_INTENTS_V1={version=1,owner=0,serial=1,
                operations={['1']={token='purchase:0:1',sequence=1,cityID=65536,
                  unitType='UNIT_NATURALIST',unitHash=1877270220,x=16,y=14,cost=300,
                  faithBefore=400,reserve=100,turn=92,stage='ARMED',baselineUnitIDs={}}}}
            end
            return original(...)
          end
        ''')
        self.assertFalse(self.prepare()[0])
        self.assertEqual((self.op().stage,self.h.writes), ('ARMED',0))


if __name__ == '__main__':
    unittest.main()
