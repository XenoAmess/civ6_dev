import unittest
from purchase_intent_harness import ROOT, KEY, make_purchase_core


class PurchaseReceiptEvents(unittest.TestCase):
    def setUp(self):
        self.lua = make_purchase_core(with_receipt_events=True)
        self.h = self.lua.globals().H
        self.bridge = self.lua.globals().ExposedMembers.BaiqiNaturalistPurchaseBridge
        self.source = (ROOT / 'mod/Baiqi/Lua/BaiqiNaturalistPurchaseIntentGameplay.lua').read_text(encoding='utf-8')

    def arm(self):
        self.assertTrue(self.bridge.Prepare(0,65536,16,14,1877270220,300,400,100)[0])

    def test_two_static_events_share_one_callback_and_observe_actual_facts(self):
        self.assertEqual((self.h.adds,self.h.ListenerCount('UnitAddedToMap'),self.h.ListenerCount('PlayerTurnDeactivated')), (2,1,1))
        self.assertTrue(self.lua.eval("function() local a=next(H.listeners.UnitAddedToMap);local b=next(H.listeners.PlayerTurnDeactivated);return a==b end")())
        self.arm()
        self.lua.execute('AddPurchasedUnit(6000000);S.faith=100')
        self.h.Fire('UnitAddedToMap',0,6000000)
        self.assertEqual(self.h.store[KEY].operations['1'].stage, 'OBSERVED')

    def test_foreign_or_incomplete_event_never_confirms_and_inactive_deactivation_can(self):
        self.arm()
        before = self.h.reads
        self.h.Fire('UnitAddedToMap',1,6000000)
        self.assertEqual(self.h.reads, before)
        self.lua.execute('AddPurchasedUnit(6000000)')
        self.h.Fire('UnitAddedToMap',0,6000000)
        self.assertEqual(self.h.store[KEY].operations['1'].stage, 'ARMED')
        self.lua.execute('S.faith=100;H.active=false')
        self.h.Fire('PlayerTurnDeactivated',0)
        self.assertEqual(self.h.store[KEY].operations['1'].stage, 'OBSERVED')

    def test_duplicate_include_cleans_only_owned_hooks_and_shutdown_is_idempotent(self):
        self.lua.execute("H.foreign=function() H.foreignCalls=(H.foreignCalls or 0)+1 end;Events.UnitAddedToMap.Add(H.foreign)")
        self.lua.execute(self.source)
        self.assertEqual((self.h.ListenerCount('UnitAddedToMap'),self.h.ListenerCount('PlayerTurnDeactivated')), (2,1))
        module = self.lua.globals().BaiqiNaturalistPurchaseIntentGameplay
        module.Shutdown()
        module.Shutdown()
        self.assertEqual((self.h.ListenerCount('UnitAddedToMap'),self.h.ListenerCount('PlayerTurnDeactivated')), (1,0))
        before = self.h.reads
        self.h.Fire('UnitAddedToMap',0,6000000)
        self.assertEqual(self.h.reads, before)
        self.assertEqual(self.h.foreignCalls, 1)

    def test_shutdown_uses_captured_remove_when_event_name_is_replaced(self):
        self.lua.execute("Events.UnitAddedToMap={Remove=function() error('foreign replacement') end}")
        self.lua.globals().BaiqiNaturalistPurchaseIntentGameplay.Shutdown()
        self.assertEqual(self.h.ListenerCount('UnitAddedToMap'), 0)
        self.assertEqual(self.h.removes, 2)

    def test_foreign_module_and_bridge_are_preserved(self):
        self.lua.globals().BaiqiNaturalistPurchaseIntentGameplay.Shutdown()
        self.lua.execute("H.foreignModule={marker='foreign',Shutdown=function() error('foreign module') end};BaiqiNaturalistPurchaseIntentGameplay=H.foreignModule")
        result = self.lua.execute(self.source)
        self.assertTrue(self.lua.eval('rawequal')(result,self.h.foreignModule))
        self.assertEqual(self.h.ListenerCount('UnitAddedToMap'), 0)
        self.lua.execute("BaiqiNaturalistPurchaseIntentGameplay=nil;H.foreignBridge={version=99,marker='foreign'};ExposedMembers.BaiqiNaturalistPurchaseBridge=H.foreignBridge")
        self.lua.execute(self.source)
        self.assertTrue(self.lua.eval('rawequal')(self.lua.globals().ExposedMembers.BaiqiNaturalistPurchaseBridge,self.h.foreignBridge))
        self.assertEqual(self.h.ListenerCount('PlayerTurnDeactivated'), 0)

    def test_malformed_event_does_not_block_other_hook_or_module(self):
        self.lua.globals().BaiqiNaturalistPurchaseIntentGameplay.Shutdown()
        self.lua.execute("Events.UnitAddedToMap=setmetatable({},{__index=function() error('unavailable event') end})")
        self.lua.execute(self.source)
        self.assertEqual((self.h.ListenerCount('UnitAddedToMap'),self.h.ListenerCount('PlayerTurnDeactivated')), (0,1))
        self.assertEqual(self.bridge.Inspect(0)[0], 'OPEN')

    def test_malformed_prior_and_bridge_namespace_do_not_throw_or_overwrite(self):
        self.lua.globals().BaiqiNaturalistPurchaseIntentGameplay.Shutdown()
        self.lua.execute("H.foreignModule=setmetatable({},{__index=function() error('foreign') end});BaiqiNaturalistPurchaseIntentGameplay=H.foreignModule")
        result = self.lua.execute(self.source)
        self.assertTrue(self.lua.eval('rawequal')(result,self.h.foreignModule))
        self.lua.execute("BaiqiNaturalistPurchaseIntentGameplay=nil;ExposedMembers=setmetatable({},{__index=function() error('namespace') end})")
        self.lua.execute(self.source)
        self.assertEqual(self.h.ListenerCount('UnitAddedToMap'), 0)


if __name__ == '__main__':
    unittest.main()
