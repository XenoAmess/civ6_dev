"""A fresh, unsent founding grant may wait; saved ARMED is never a grant."""
from pathlib import Path
import unittest

from tests import test_baiqi_found_city_receipt as receipt

ROOT = Path(__file__).resolve().parents[1]


class FoundCityLiveDispatchTests(unittest.TestCase):
    def setUp(self):
        self.h = receipt.FoundCityReceiptTests()
        self.h.setUp()
        self.lua, self.w = self.h.lua, self.h.w
        self.lua.execute('''
          local w=TestWorld
          Events.LoadGameViewStateDone={Add=function(f)w.loadDone=f end,Remove=function()end}
        ''')
        self.reload_controller()
        self.lua.execute('''
          local w=TestWorld
          local b=ExposedMembers.BaiqiSettlementIntentBridge;local commit=b.Commit
          b.Commit=function(...)
            local a,t,r=commit(...);if a==true then w.holdFound=true end;return a,t,r
          end
          local qualify=UnitManager.CanStartOperation
          UnitManager.CanStartOperation=function(u,op,...)
            if op==11 and w.holdFound then return false end
            if op==11 and w.reenter then BaiqiController.RunNow()end
            return qualify(u,op,...)
          end
        ''')

    def reload_controller(self):
        self.lua.execute((ROOT / 'mod/Baiqi/Lua/BaiqiController.lua').read_text(encoding='utf-8'))
        self.h.controller = self.lua.globals().BaiqiController

    def arm_without_order(self):
        self.h.run_now(2)
        self.assertEqual(self.h.found_count(), 0)
        self.assertEqual(self.w.settlementBank.operations['2'].stage, 'ARMED')

    def resume(self, count=3):
        self.w.holdFound = False
        self.h.run_now(count)

    def test_transient_pre_writer_rejection_can_dispatch_once_in_same_turn(self):
        self.arm_without_order()
        self.resume()
        self.assertEqual(self.h.found_count(), 1)
        self.assertEqual(self.w.settlementBank.operations['2'].stage, 'ARMED')
        self.assertEqual(self.h.observed(), [])

    def test_passive_reconciliation_does_not_dispatch_or_consume_grant(self):
        self.arm_without_order()
        self.w.holdFound = False
        for _ in range(3):
            self.h.controller.RunNow(False)
        self.assertEqual(len(self.w.unitRequests), 0)
        self.h.run_now(3)
        self.assertEqual(self.h.found_count(), 1)

    def test_busy_core_defers_until_idle(self):
        self.arm_without_order()
        self.w.holdFound, self.w.busy = False, True
        self.h.run_now(2)
        self.assertEqual(self.h.found_count(), 0)
        self.w.busy = False
        self.h.run_now(3)
        self.assertEqual(self.h.found_count(), 1)

    def test_qualification_callback_cannot_reenter_dispatch(self):
        self.arm_without_order()
        self.w.reenter = True
        self.resume(5)
        self.assertEqual(self.h.found_count(), 1)

    def test_escort_blocks_then_fresh_single_unit_can_dispatch(self):
        self.arm_without_order()
        self.w.formation = 2
        self.resume()
        self.assertEqual(self.h.found_count(), 0)
        self.w.formation = 1
        self.h.run_now(3)
        self.assertEqual(self.h.found_count(), 1)

    def test_full_id_alias_blocks_native_order(self):
        self.arm_without_order()
        self.w.unitAlias = True
        self.resume()
        self.assertEqual(self.h.found_count(), 0)
        self.w.unitAlias = False
        self.h.run_now(3)
        self.assertEqual(self.h.found_count(), 1)

    def test_native_false_is_one_entered_call_not_retry_permission(self):
        self.lua.execute('local old=UnitManager.RequestOperation;UnitManager.RequestOperation=function(...)old(...);return false end')
        self.arm_without_order()
        self.resume(6)
        self.assertEqual(self.h.found_count(), 1)

    def test_native_void_is_one_entered_call_not_retry_permission(self):
        self.lua.execute('local old=UnitManager.RequestOperation;UnitManager.RequestOperation=function(...)old(...)end')
        self.arm_without_order()
        self.resume(6)
        self.assertEqual(self.h.found_count(), 1)

    def test_native_applies_then_throws_is_never_replayed(self):
        self.lua.execute('local old=UnitManager.RequestOperation;UnitManager.RequestOperation=function(...)old(...);error("AFTER_NATIVE")end')
        self.arm_without_order()
        self.resume(6)
        self.assertEqual(self.h.found_count(), 1)

    def test_native_throws_before_visible_effect_is_also_never_replayed(self):
        self.lua.execute('UnitManager.RequestOperation=function()TestWorld.writerEntries=(TestWorld.writerEntries or 0)+1;error("UNKNOWN_NATIVE")end')
        self.arm_without_order()
        self.resume(6)
        self.assertEqual(self.w.writerEntries, 1)
        self.assertEqual(self.h.found_count(), 0)
        self.assertEqual(self.w.settlementBank.operations['2'].stage, 'ARMED')

    def test_controller_reload_does_not_recreate_live_permission(self):
        self.arm_without_order()
        self.reload_controller()
        self.resume(5)
        self.assertEqual(self.h.found_count(), 0)

    def test_world_load_event_drops_permission_even_if_bindings_are_reused(self):
        self.arm_without_order()
        self.w.loadDone()
        self.resume(5)
        self.assertEqual(self.h.found_count(), 0)

    def test_next_turn_does_not_recreate_same_turn_permission(self):
        self.arm_without_order()
        self.w.turn += 1
        self.resume(5)
        self.assertEqual(self.h.found_count(), 0)

    def test_foreign_city_conflict_stays_held(self):
        self.arm_without_order()
        self.w.cityEffect, self.w.effectOwner = True, 8
        self.w.siteOwners[42] = 8
        self.resume(3)
        self.w.effectOwner, self.w.siteOwners[42] = 7, 7
        self.h.run_now(3)
        self.assertEqual(self.h.found_count(), 0)
        self.assertEqual(self.h.observed(), [])

    def test_changed_native_writer_does_not_inherit_old_grant(self):
        self.arm_without_order()
        self.lua.execute('local old=UnitManager.RequestOperation;UnitManager.RequestOperation=function(...)return old(...)end')
        self.resume(4)
        self.assertEqual(self.h.found_count(), 0)

    def test_journal_request_change_is_not_the_original_live_grant(self):
        self.arm_without_order()
        self.w.settlementBank.operations['2'].requestID = '7:1:999'
        self.resume(4)
        self.assertEqual(self.h.found_count(), 0)

    def test_world_load_during_commit_ack_cannot_create_a_new_live_grant(self):
        self.lua.execute('''
          local b=ExposedMembers.BaiqiSettlementIntentBridge;local old=b.Commit
          b.Commit=function(...)local a,t,r=old(...);TestWorld.loadDone();return a,t,r end
        ''')
        self.arm_without_order()
        self.resume(5)
        self.assertEqual(self.h.found_count(), 0)

    def test_operation_enum_change_does_not_inherit_old_permission(self):
        self.arm_without_order()
        self.lua.execute('UnitOperationTypes.FOUND_CITY=999')
        self.resume(4)
        self.assertEqual(self.h.found_count(), 0)

    def test_unknown_queue_waits_without_moving_escort(self):
        self.lua.execute('''
          UnitManager.GetQueuedDestination=function()return TestWorld.queuedDestination end
        ''')
        self.arm_without_order()
        self.w.queuedDestination = 43
        self.resume()
        self.assertEqual(self.h.found_count(), 0)
        self.w.queuedDestination = None
        self.h.run_now(3)
        self.assertEqual(self.h.found_count(), 1)

    def test_queue_read_callback_cannot_attach_an_escort_and_dispatch(self):
        self.lua.execute('''
          UnitManager.GetQueuedDestination=function()
            if TestWorld.attachEscort then TestWorld.formation=2 end
            return nil
          end
        ''')
        self.arm_without_order()
        self.w.attachEscort = True
        self.resume()
        self.assertEqual(self.h.found_count(), 0)
        self.w.attachEscort, self.w.formation = False, 1
        self.h.run_now(3)
        self.assertEqual(self.h.found_count(), 1)

    def test_native_writer_callback_cannot_reenter_first_dispatch(self):
        self.lua.execute('''
          local old=UnitManager.RequestOperation
          UnitManager.RequestOperation=function(...)
            BaiqiController.RunNow();return old(...)
          end
        ''')
        self.arm_without_order()
        self.resume(5)
        self.assertEqual(self.h.found_count(), 1)

    def test_missing_commit_ack_never_creates_live_permission(self):
        self.lua.execute('''
          local b=ExposedMembers.BaiqiSettlementIntentBridge;local old=b.Commit
          b.Commit=function(...)old(...);error('LOST_ACK')end
        ''')
        self.arm_without_order()
        self.resume(5)
        self.assertEqual(self.h.found_count(), 0)

    def test_unsent_grant_is_not_spent_by_the_standby_timeout(self):
        self.lua.execute('''
          GameInfo.UnitOperations={UNITOPERATION_SKIP_TURN={Hash=17}};ActivityTypes={ACTIVITY_AWAKE=1}
          UnitManager.GetActivityType=function()return 1 end
          local u=TestWorld.objects.settler
          u.IsReadyToSelect=function()return true end;u.IsReadyToMove=function()return true end
        ''')
        self.arm_without_order()
        self.h.controller.Update(3)
        self.assertEqual(len(self.w.unitRequests), 0)
        self.resume(4)
        self.assertEqual(self.h.found_count(), 1)


if __name__ == '__main__':
    unittest.main()
