import unittest
from missionary_purchase_core_harness import make_missionary_core,ROOT,KEY,NKEY,RKEY
from purchase_intent_harness import make_purchase_core


class MissionaryPurchaseIntentTests(unittest.TestCase):
    def setUp(self):
        self.lua=make_missionary_core()
        self.h=self.lua.globals().H
        self.s=self.lua.globals().S
        self.bridge=self.lua.globals().ExposedMembers.BaiqiMissionaryPurchaseBridge

    def prepare(self,**changes):
        values=dict(pid=0,cityID=65536,x=16,y=14,unitHash=-199,religionIndex=4,cost=75,faithBefore=175,reserve=100)
        values.update(changes)
        return self.bridge.Prepare(*(values[k]for k in ('pid','cityID','x','y','unitHash','religionIndex','cost','faithBefore','reserve')))

    def op(self):
        return self.h.store[KEY].operations['1']

    def effect(self):
        self.lua.execute('H.Add(6000000);S.faith=100')

    def test_nil_inspect_does_not_write_or_initialize_purchase(self):
        self.assertEqual(self.bridge.Inspect(0)[0],'OPEN')
        self.assertEqual(self.h.writes,0)
        self.assertIsNone(self.h.store[KEY])

    def test_permission_persists_once_before_any_effect(self):
        self.assertEqual(self.prepare()[:2],(True,'missionary-purchase:0:1'))
        self.assertEqual((self.h.writes,self.op().stage,self.op().religionIndex),(1,'ARMED',4))
        self.assertEqual(len(self.lua.globals().records),0)
        self.assertFalse(self.prepare()[0])
        self.assertEqual(self.h.writes,1)

    def test_fresh_spread_namespace_is_initialized_before_armed(self):
        self.h.store[RKEY]=None
        self.assertTrue(self.prepare()[0])
        self.assertEqual(list(self.h.history.values()),[RKEY,KEY])
        self.effect()
        self.assertEqual(self.lua.globals().ExposedMembers.BaiqiReligiousIntentBridge.Inspect(0,6000000)[0],'OPEN')
        self.assertEqual(self.h.store[RKEY].serial,0)

    def test_spread_write_failure_prevents_purchase_permission(self):
        self.h.store[RKEY]=None
        self.h.rejectKey=RKEY
        self.assertFalse(self.prepare()[0])
        self.assertIsNone(self.h.store[KEY])

    def test_new_actor_and_exact_faith_debit_are_observed_once(self):
        self.assertTrue(self.prepare()[0])
        self.effect()
        self.assertEqual(self.bridge.Inspect(0,'missionary-purchase:0:1')[:2],('OBSERVED','missionary-purchase:0:1'))
        self.assertEqual((self.op().newUnitID,self.op().faithAfter,self.h.writes),(6000000,100,2))
        self.assertEqual(self.bridge.Inspect(0)[0],'OPEN')
        self.assertEqual(self.h.writes,2)

    def test_missing_wrong_debit_religion_city_turn_or_escort_never_confirms(self):
        for setup in ('S.faith=100','H.Add(6000000)','H.Add(6000000);S.faith=101',
                      'H.Add(6000000);S.faith=100;H.turn=120',
                      'H.Add(6000000);S.faith=100;S.created=5',
                      'H.Add(6000000);S.faith=100;S.majority=5',
                      'H.Add(6000000);S.faith=100;S.owner=1',
                      'H.Add(6000000);S.faith=100;H.newUnit.religion=5',
                      'H.Add(6000000);S.faith=100;H.newUnit.charges=0',
                      'H.Add(6000000);S.faith=100;H.newUnit.x=17',
                      'H.Add(6000000);S.faith=100;H.newUnit.formation=2',
                      'H.Add(6000000);H.Add(6000001);S.faith=100'):
            with self.subTest(setup=setup):
                self.setUp();self.assertTrue(self.prepare()[0]);self.lua.execute(setup)
                self.assertEqual((self.bridge.Inspect(0)[0],self.op().stage,self.h.writes),('ARMED','ARMED',1))

    def test_baseline_preserves_foreign_faith_and_zero_charges(self):
        self.lua.execute('H.Add(17).religion=5;H.Add(11).charges=0')
        self.assertTrue(self.prepare()[0])
        self.assertEqual(list(self.op().baselineUnitIDs.values()),[11,17])
        self.effect()
        self.assertEqual(self.bridge.Inspect(0)[0],'OPEN')
        self.assertEqual(self.op().newUnitID,6000000)

    def test_converted_or_recharged_existing_id_is_not_new_purchase(self):
        for setup in ('H.Add(17).religion=5','H.Add(17).charges=0'):
            with self.subTest(setup=setup):
                self.setUp();self.lua.execute(setup);self.assertTrue(self.prepare()[0])
                self.lua.execute('records[1].religion=4;records[1].charges=3;S.faith=100')
                self.assertEqual(self.bridge.Inspect(0)[0],'ARMED')

    def test_own_religion_stock_counts_immobile_and_escorted_units(self):
        for setup in ('H.Add(17)','H.Add(17).formation=2','H.Add(17).moves=0'):
            with self.subTest(setup=setup):
                self.setUp();self.lua.execute(setup);self.assertFalse(self.prepare()[0]);self.assertEqual(self.h.writes,0)

    def test_owner_majority_price_metadata_and_quote_boundaries(self):
        for setup in ('H.localPlayer=1','H.human=false','H.active=false',"H.leader='LEADER_OTHER'",
                      'H.multiplayer=true','H.hotseat=true','S.majority=5','S.created=-1','S.faith=174',
                      'GameInfo.Units[17].MustPurchase=false',"GameInfo.Units[17].PurchaseYield='YIELD_GOLD'",
                      'GameInfo.Units[17].Hash=-198'):
            with self.subTest(setup=setup):
                self.setUp();self.lua.execute(setup);self.assertFalse(self.prepare()[0]);self.assertEqual(self.h.writes,0)
        for change in ({'religionIndex':-1},{'religionIndex':True},{'cost':76},{'reserve':101},{'unitHash':True}):
            with self.subTest(change=change):
                self.setUp();self.assertFalse(self.prepare(**change)[0]);self.assertEqual(self.h.writes,0)

    def test_unknown_or_failed_storage_is_preserved(self):
        for setup in ("H.store.BAIQI_MISSIONARY_PURCHASE_INTENTS_V1='unknown'",
                      'H.throwRead=true','H.allowWrite=false','H.throwWrite=true','H.corruptWrite=true'):
            with self.subTest(setup=setup):
                self.setUp();self.lua.execute(setup);self.assertFalse(self.prepare()[0])
        self.setUp();self.h.store[KEY]='unknown'
        self.assertEqual(self.bridge.Inspect(0)[0],'UNKNOWN')
        self.assertEqual((self.h.store[KEY],self.h.writes),('unknown',0))

    def test_failed_receipt_write_retains_armed(self):
        self.assertTrue(self.prepare()[0]);self.effect();self.h.allowWrite=False
        self.assertEqual(self.bridge.Inspect(0)[0],'UNKNOWN')
        self.assertEqual(self.op().stage,'ARMED')
        self.assertFalse(self.prepare()[0])

    def test_reload_keeps_unresolved_and_never_regrants(self):
        self.assertTrue(self.prepare()[0])
        saved=self.h.Copy(self.h.store)
        lua=make_missionary_core(stored=saved)
        bridge=lua.globals().ExposedMembers.BaiqiMissionaryPurchaseBridge
        self.assertEqual(bridge.Inspect(0)[0],'ARMED')
        self.assertFalse(bridge.Prepare(0,65536,16,14,-199,4,75,175,100)[0])
        self.assertEqual(lua.globals().H.writes,0)

    def test_last_snapshot_unknown_or_baseline_change_prevents_permission(self):
        for change in ("return nil","H.Add(17).religion=5;return original(...)","S.faith=174;return original(...)"):
            with self.subTest(change=change):
                self.setUp()
                self.lua.execute('local original=BaiqiMissionaryPurchaseSnapshot.Read;local n=0;'
                  'BaiqiMissionaryPurchaseSnapshot.Read=function(...)n=n+1;if n==3 then '+change+' end;return original(...)end')
                self.assertFalse(self.prepare()[0]);self.assertIsNone(self.h.store[KEY])

    def test_initialization_cannot_hide_a_changed_purchase_journal(self):
        for changed in ("'concurrent'","{version=1,owner=0,serial=17,operations={}}"):
            with self.subTest(changed=changed):
                self.setUp()
                self.lua.execute('''
                  local old=BaiqiReligiousIntentGameplay.Initialize
                  BaiqiReligiousIntentGameplay.Initialize=function(pid)
                    local ok=old(pid);H.store.BAIQI_MISSIONARY_PURCHASE_INTENTS_V1='''+changed+''';return ok
                  end
                ''')
                self.assertFalse(self.prepare()[0])
                if changed=="'concurrent'":
                    self.assertEqual(self.h.store[KEY],'concurrent')
                else:
                    self.assertEqual(self.h.store[KEY].serial,17)
                self.assertEqual(self.h.writes,0)

    def test_naturalist_armed_or_corrupt_namespace_holds_missionary(self):
        for setup in ("H.store.BAIQI_NATURALIST_PURCHASE_INTENTS_V1='unknown'",'''
          H.store.BAIQI_NATURALIST_PURCHASE_INTENTS_V1={version=1,owner=0,serial=1,operations={
            ['1']={token='purchase:0:1',sequence=1,cityID=65536,unitType='UNIT_NATURALIST',
              unitHash=9,x=16,y=14,cost=75,faithBefore=175,reserve=100,turn=119,stage='ARMED',baselineUnitIDs={}}}}
        '''):
            with self.subTest(setup=setup):
                self.setUp();self.lua.execute(setup);self.assertFalse(self.prepare()[0]);self.assertEqual(self.h.writes,0)

    def test_missionary_armed_or_corrupt_namespace_holds_naturalist(self):
        self.assertTrue(self.prepare()[0])
        state=self.h.Copy(self.h.store[KEY])
        lua=make_purchase_core();lua.globals().H.store[KEY]=None
        # Cross-runtime values must be copied through plain Python, as with a save.
        def plain(v):return {k:plain(x)for k,x in v.items()}if hasattr(v,'items')else v
        def into(v):return lua.table_from({k:into(x)for k,x in v.items()})if isinstance(v,dict)else v
        lua.globals().H.store[KEY]=into(plain(state))
        bridge=lua.globals().ExposedMembers.BaiqiNaturalistPurchaseBridge
        self.assertFalse(bridge.Prepare(0,65536,16,14,1877270220,300,400,100)[0])
        self.assertEqual(lua.globals().H.writes,0)
        lua.globals().H.store[KEY]='unknown'
        self.assertFalse(bridge.Prepare(0,65536,16,14,1877270220,300,400,100)[0])

    def test_initialize_preserves_legacy_and_armed_spread_records(self):
        self.lua.execute('H.Add(17);H.store.BAIQI_RELIGIOUS_INTENTS_V1=nil')
        init=self.lua.globals().BaiqiReligiousIntentGameplay.Initialize
        self.assertTrue(init(0))
        self.assertEqual(self.h.store[RKEY].operations['17'].stage,'LEGACY_UNKNOWN')
        self.lua.execute('''
          local op=H.store.BAIQI_RELIGIOUS_INTENTS_V1.operations['17']
          op.stage='ARMED';op.cityID=65536;op.cityX=16;op.cityY=14
        ''')
        writes=self.h.writes
        self.assertTrue(init(0))
        self.assertEqual((self.h.store[RKEY].operations['17'].stage,self.h.writes),('ARMED',writes))

    def test_initialize_handles_pid_zero_exceptions_and_foreign_bridge(self):
        init=self.lua.globals().BaiqiReligiousIntentGameplay.Initialize
        self.assertTrue(init(0))
        for pid in (True,-1,1,'0',None):
            self.assertFalse(init(pid))
        self.h.throwRead=True
        self.assertFalse(init(0))
        self.h.throwRead=False
        self.lua.execute('ExposedMembers.BaiqiReligiousIntentBridge={}')
        self.assertFalse(init(0))
        self.assertFalse(self.prepare()[0])

    def test_unknown_token_and_inactive_receipt(self):
        self.assertTrue(self.prepare()[0])
        for token in ('missionary-purchase:1:1','missionary-purchase:0:01',1):
            self.assertEqual(self.bridge.Inspect(0,token)[0],'UNKNOWN')
        self.effect();self.h.active=False
        self.assertEqual(self.bridge.Inspect(0,'missionary-purchase:0:1')[0],'OBSERVED')

    def test_owned_events_observe_once_and_hotreload_removes_old_listeners(self):
        self.assertEqual((self.h.adds,self.h.removes),(2,0))
        self.assertTrue(self.prepare()[0]);self.effect()
        self.h.Fire('UnitAddedToMap',0)
        self.assertEqual((self.op().stage,self.h.writes),('OBSERVED',2))
        self.h.Fire('PlayerTurnDeactivated',0)
        self.assertEqual(self.h.writes,2)
        old=self.bridge
        self.lua.execute((ROOT/'mod/Baiqi/Lua/BaiqiMissionaryPurchaseIntentGameplay.lua').read_text(encoding='utf-8'))
        self.assertEqual((self.h.adds,self.h.removes),(4,2))
        self.assertEqual(self.h.ListenerCount('UnitAddedToMap'),1)
        self.assertEqual(old.Inspect(0)[0],'UNAVAILABLE')

    def test_foreign_bridge_rebind_disables_old_alias_and_callbacks(self):
        self.assertTrue(self.prepare()[0]);self.effect()
        self.lua.execute('ExposedMembers.BaiqiMissionaryPurchaseBridge={version=99}')
        self.h.Fire('UnitAddedToMap',0)
        self.assertEqual((self.op().stage,self.h.writes),('ARMED',1))
        self.assertEqual(self.bridge.Inspect(0)[0],'UNAVAILABLE')
        self.assertFalse(self.prepare()[0])

    def test_strict_initializer_and_guard_boolean(self):
        for setup in ('BaiqiReligiousIntentGameplay.Initialize=function()return 1 end',
                      'BaiqiFaithPurchaseGuard.Open=function()return 1 end'):
            with self.subTest(setup=setup):
                self.setUp();self.lua.execute(setup);self.assertFalse(self.prepare()[0]);self.assertEqual(self.h.writes,0)


if __name__=='__main__':
    unittest.main()
