"""The actual UI consumer must survive loss of in-memory founding receipts."""
from pathlib import Path
import unittest
from tests import test_baiqi_found_city_receipt as receipt_fixture

ROOT=Path(__file__).resolve().parents[1]

class SettlementPersistentUI(unittest.TestCase):
    def setUp(self):
        self.h=receipt_fixture.FoundCityReceiptTests()
        self.h.setUp()
        self.lua=self.h.lua
        self.w=self.h.w

    def reload_controller(self):
        self.lua.execute((ROOT/'mod/Baiqi/Lua/BaiqiController.lua').read_text(encoding='utf-8'))
        self.h.controller=self.lua.globals().BaiqiController

    def test_restore_armed_without_replay(self):
        self.h.issue()
        self.reload_controller()
        self.h.run_now(3)
        self.w.turn+=1
        self.h.run_now(2)
        self.assertEqual(self.h.found_count(),1)
        self.assertEqual(self.h.observed(),[])

    def test_restore_missing_actor_then_late_city(self):
        self.h.issue()
        self.w.withSettler=False
        self.reload_controller()
        self.h.run_now(2)
        self.assertEqual(self.h.observed(),[])
        self.w.cityEffect=True
        self.h.run_now(2)
        self.assertEqual(len(self.h.observed()),1)
        self.assertEqual(self.h.found_count(),1)

    def test_native_call_applies_then_throws_stays_pending(self):
        self.lua.execute('local old=UnitManager.RequestOperation;UnitManager.RequestOperation=function(...)old(...);error("APPLIED_THEN_THROW")end')
        self.h.issue()
        self.reload_controller()
        self.h.run_now(3)
        self.assertEqual(self.h.found_count(),1)
        self.h.effect()
        self.h.run_now(2)
        self.assertEqual(len(self.h.observed()),1)

    def test_commit_ack_lost_never_emits_or_regrants(self):
        self.lua.execute('local b=ExposedMembers.BaiqiSettlementIntentBridge;local old=b.Commit;b.Commit=function(...)old(...);error("ACK_LOST")end')
        self.h.run_now(2)
        self.assertEqual(self.h.found_count(),0)
        self.assertEqual(self.w.settlementBank.operations['2'].stage,'ARMED')
        self.reload_controller()
        self.w.turn+=1
        self.h.run_now(3)
        self.assertEqual(self.h.found_count(),0)
        self.w.cityEffect=True
        self.w.queueSize=0
        self.h.run_now(2)
        self.assertGreater(len(self.w.cityRequests),0,'Other cities continue while one settler is held')

    def after_commit(self,change):
        self.lua.execute('local b=ExposedMembers.BaiqiSettlementIntentBridge;local old=b.Commit;b.Commit=function(...)local g,t,r=old(...);'+change+';return g,t,r end')
        self.h.run_now(2)
        self.assertEqual(self.h.found_count(),0)
        self.assertEqual(self.w.settlementBank.operations['2'].stage,'ARMED')

    def test_escort_created_after_ack_prevents_order(self):
        self.after_commit('TestWorld.formation=2')

    def test_city_appears_after_ack_prevents_order(self):
        self.after_commit('TestWorld.cityEffect=true')

    def test_native_legality_changes_after_ack_prevents_order(self):
        self.after_commit('UnitManager.CanStartOperation=function()return false end')

    def test_player_changes_after_ack_prevents_order(self):
        self.after_commit('Game.GetLocalPlayer=function()return 8 end')

    def test_loaded_old_settler_migrates_to_unknown(self):
        self.w.missingSettlementBank=True
        self.h.controller.SetSettlementLoadKind(True)
        self.h.run_now(2)
        self.assertEqual(self.h.found_count(),0)
        self.assertEqual(self.w.settlementBank.operations['2'].stage,'LEGACY_UNKNOWN')
        self.reload_controller()
        self.h.controller.SetSettlementLoadKind(False)
        self.h.run_now(2)
        self.assertEqual(self.h.found_count(),0)
        self.assertEqual(self.w.settlementBank.operations['2'].stage,'LEGACY_UNKNOWN')

    def test_new_game_typed_false_allows_first_settler(self):
        self.w.missingSettlementBank=True
        self.h.controller.SetSettlementLoadKind(False)
        self.h.issue()

    def test_missing_load_kind_cannot_initialize(self):
        self.w.missingSettlementBank=True
        self.h.run_now(2)
        self.assertIsNone(self.w.settlementBank)
        self.assertEqual(self.h.found_count(),0)

    def test_unissued_prepared_replaced_with_fresh_token(self):
        self.lua.execute('local b=ExposedMembers.BaiqiSettlementIntentBridge;assert(b.Initialize(7,false)=="READY");local s,op=b.Prepare(7,2,42,2,3,"7:1:900");assert(s=="PREPARED");TestWorld.oldToken=op.token')
        self.h.issue()
        self.assertNotEqual(self.w.oldToken,self.w.settlementBank.operations['2'].token)

    def test_foreign_conflict_latch_survives_controller_reload(self):
        self.h.issue()
        self.h.effect()
        self.w.effectOwner=8
        self.w.siteOwners[42]=8
        self.h.run_now()
        self.assertTrue(self.w.settlementBank.operations['2'].conflictingCity)
        self.reload_controller()
        self.w.effectOwner=7
        self.w.siteOwners[42]=7
        self.h.run_now(3)
        self.assertEqual(self.h.observed(),[])
        self.assertEqual(self.h.found_count(),1)

    def test_exact_offmap_delayed_actor_can_correlate_with_city(self):
        self.h.issue()
        self.w.cityEffect=True
        self.lua.execute('local u=TestWorld.objects.settler;u.GetX=function()return -9999 end;u.GetY=function()return -9999 end;u.IsDelayedDeath=function()return true end')
        self.h.run_now(2)
        self.assertEqual(len(self.h.observed()),1)
        self.assertEqual(self.h.found_count(),1)

    def test_large_legacy_metadata_never_enters_native_findid(self):
        self.lua.execute('''
          TestWorld.withSettler=false;local J=BaiqiSettlementJournal;local b=J.New(7);b.serial=1
          b.operations['9007199254740991']={token=J.Token(7,1),sequence=1,unitID=9007199254740991,
            unitType='UNIT_SETTLER',turn=1,requestID='legacy',stage='LEGACY_UNKNOWN',empty=false,conflictingCity=false}
          TestWorld.settlementBank=b;local p=TestWorld.objects.player;local old=p.GetUnits
          p.GetUnits=function(...)local a=old(...);local find=a.FindID;a.FindID=function(self,id)assert(id<=2147483647);return find(self,id)end;return a end
        ''')
        self.h.run_now(2)
        self.assertEqual(self.h.found_count(),0)

    def test_pending_route_is_not_overwritten_by_standby(self):
        self.w.missingSettlementBank=True
        self.h.controller.SetSettlementLoadKind(True)
        self.lua.execute('''
          GameInfo.UnitOperations={UNITOPERATION_SKIP_TURN={Hash=17}};ActivityTypes={ACTIVITY_AWAKE=1}
          UnitManager.GetActivityType=function()return 1 end;UnitManager.GetQueuedDestination=function()return 43 end
          local u=TestWorld.objects.settler;u.IsReadyToSelect=function()return true end;u.IsReadyToMove=function()return true end
        ''')
        self.h.run_now(3)
        self.assertEqual(len(self.w.unitRequests),0)

if __name__=='__main__':unittest.main()
