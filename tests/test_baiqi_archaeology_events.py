import unittest
from archaeology_intent_harness import ROOT, KEY, archaeology_runtime


class ArchaeologyEventTests(unittest.TestCase):
    def setUp(self):
        self.lua, self.core, self.h = archaeology_runtime(with_events=True)
        self.source = (ROOT / 'mod/Baiqi/Lua/BaiqiArchaeologyReceiptEvents.lua').read_text(encoding='utf-8')

    def bind(self):
        return self.lua.execute(self.source)

    def choice(self):
        b = self.core.bridge
        self.assertTrue(b.PrepareExcavation(7, 4, self.h.proposal)[0])
        self.assertTrue(b.PrepareChoice(7, 4, 'archaeology:7:1', self.h.descriptor)[0])

    def stage(self):
        return self.h.store[KEY].operations['4'].stage

    def test_static_event_forwards_real_payload_to_actual_core_consumer(self):
        self.choice()
        module = self.bind()
        self.assertEqual((module.marker, self.h.ListenerCount()), ('baiqi-archaeology-receipt-events-v1', 1))
        self.h.Emit(8, 4, 2, 3, 24, 101)
        self.assertEqual(self.stage(), 'CHOICE_ARMED')
        self.h.Emit(7, 4, 2, 3, 24, 101)
        self.assertEqual((self.stage(), self.h.store[KEY].operations['4'].newWorkID, self.h.writes), ('OBSERVED', 101, 3))
        self.h.Emit(7, 4, 2, 3, 24, 101)
        self.assertEqual(self.h.writes, 3)

    def test_repeat_include_cleans_only_prior_owned_callback(self):
        self.lua.execute('H.foreign=function() H.foreignCalls=(H.foreignCalls or 0)+1 end;Events.GreatWorkCreated.Add(H.foreign)')
        first = self.bind()
        second = self.bind()
        self.assertEqual((self.h.ListenerCount(), self.h.removes), (2, 1))
        first.Shutdown()
        self.assertEqual(self.h.ListenerCount(), 2)
        second.Shutdown()
        second.Shutdown()
        self.assertEqual((self.h.ListenerCount(), self.h.removes), (1, 2))
        self.h.Emit(7, 4, 2, 3, 24, 101)
        self.assertEqual(self.h.foreignCalls, 1)

    def test_cleanup_uses_original_remover_after_event_name_replacement(self):
        module = self.bind()
        self.lua.execute("Events.GreatWorkCreated={Add=function() error('new Add') end,Remove=function() error('new Remove') end}")
        module.Shutdown()
        self.assertEqual((self.h.ListenerCount(), self.h.removes), (0, 1))

    def test_foreign_root_core_or_bridge_is_preserved(self):
        for setup in (
            "BaiqiArchaeologyReceiptEvents={marker='foreign',Shutdown=function() error('foreign shutdown') end}",
            "BaiqiArchaeologyIntentGameplay={marker='foreign',version=9}",
            "ExposedMembers.BaiqiArchaeologyBridge={marker='foreign'}",
        ):
            with self.subTest(setup=setup):
                self.setUp()
                self.lua.execute(setup)
                self.bind()
                self.assertEqual(self.h.ListenerCount(), 0)

    def test_malformed_event_and_include_failure_do_not_escape(self):
        for setup in (
            "Events=setmetatable({},{__index=function() error('event provider') end})",
            "Events.GreatWorkCreated=setmetatable({},{__index=function() error('member') end})",
            "include=function() error('include unavailable') end",
        ):
            with self.subTest(setup=setup):
                self.setUp()
                self.lua.execute(setup)
                module = self.bind()
                self.assertEqual(self.h.ListenerCount(), 0)
                module.Shutdown()

    def test_foreign_or_malformed_context_after_bind_cannot_settle_receipt(self):
        for setup in (
            "ExposedMembers=setmetatable({},{__index=function() error('namespace') end})",
            "ExposedMembers.BaiqiArchaeologyBridge={marker='foreign'}",
            "BaiqiArchaeologyIntentGameplay={marker='foreign'}",
            "BaiqiArchaeologyIntentGameplay.marker='foreign'",
        ):
            with self.subTest(setup=setup):
                self.setUp()
                self.choice()
                self.bind()
                self.lua.execute(setup)
                self.h.Emit(7, 4, 2, 3, 24, 101)
                self.assertEqual(self.stage(), 'CHOICE_ARMED')
                self.assertEqual(self.h.writes, 2)

    def test_captured_callback_after_shutdown_has_no_effect(self):
        self.choice()
        module = self.bind()
        callback = next(iter(self.h.listeners.keys()))
        module.Shutdown()
        callback(7, 4, 2, 3, 24, 101)
        self.assertEqual((self.stage(), self.h.writes), ('CHOICE_ARMED', 2))

    def test_handler_exception_is_contained_and_foreign_observer_still_runs(self):
        self.lua.execute('''
          BaiqiArchaeologyIntentGameplay.ObserveCreated=function() error('core unavailable') end
          Events.GreatWorkCreated.Add(function() H.foreignCalls=(H.foreignCalls or 0)+1 end)
        ''')
        self.bind()
        self.h.Emit(7, 4, 2, 3, 24, 101)
        self.assertEqual(self.h.foreignCalls, 1)


if __name__ == '__main__':
    unittest.main()
