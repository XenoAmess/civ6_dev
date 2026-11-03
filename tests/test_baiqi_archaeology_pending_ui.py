import unittest
import test_baiqi_archaeology_ui as ui_tests
from archaeology_ui_harness import KEY


class ArchaeologyPendingUITests(unittest.TestCase):
    def setUp(self):
        self.case = ui_tests.ArchaeologyUITests()
        self.case.setUp()
        self.lua, self.w, self.h, self.c, self.logs = self.case.lua, self.case.w, self.case.h, self.case.c, self.case.logs
        self.w.pendingArtifact, self.w.missionaryMoves, self.w.archResource = True, 0, -1

    def tearDown(self):
        self.case.tearDown()

    def entry(self):
        return self.h.store[KEY].operations['4']

    def reload(self):
        self.case.reload()
        self.h, self.c = self.case.h, self.case.c

    def test_current_engine_pending_queue_migrates_without_excavation_or_move(self):
        self.lua.execute('''TestWorld.onChoice=function()
          local op=TestArchBridge.store.BAIQI_ARCHAEOLOGY_INTENTS_V1.operations['4']
          assert(op.legacy==true and op.stage=='CHOICE_ARMED' and op.resourceIndex==nil and op.resourceType==nil)
        end''')
        self.c.RunNow()
        self.assertEqual((len(self.w.choiceRequests), len(self.w.archRequests), len(self.w.unitRequests)), (1, 0, 0), self.logs)
        self.assertEqual((self.entry().legacy, self.entry().token), (True, 'archaeology:7:1'))

    def test_foreign_legacy_site_can_finish_internal_choice_without_foreign_orders(self):
        self.w.plotOwner, self.w.archResource = 8, 77
        self.c.RunNow()
        self.assertEqual((len(self.w.choiceRequests), len(self.w.unitRequests), self.w.archQualifies), (1, 0, 0), self.logs)
        self.assertIsNone(self.entry().resourceType)

    def test_real_receipt_consumer_settles_legacy_choice_even_when_unit_consumed(self):
        self.w.autoChoice, self.w.consumeArch = True, True
        self.c.RunNow()
        self.c.RunNow()
        self.assertEqual((self.entry().stage, self.entry().newWorkID, len(self.w.choiceRequests)), ('OBSERVED', 101, 1), self.logs)
        self.assertTrue(any('proof=core_created_work_receipt' in line for line in self.logs))

    def test_unknown_legacy_choice_is_not_replayed_after_cold_ui(self):
        self.w.throwChoice = True
        self.c.RunNow()
        self.assertEqual(self.entry().stage, 'CHOICE_ARMED')
        self.reload()
        self.w.turn += 1
        for _ in range(3):
            self.c.Update(3)
        self.assertEqual(len(self.w.choiceRequests), 1, self.logs)

    def test_postgrant_queue_change_holds_exact_new_token_across_reload(self):
        self.lua.execute('''local b=ExposedMembers.BaiqiArchaeologyBridge;local prepare=b.PreparePendingChoice
          b.PreparePendingChoice=function(...)
            local a,t,r=prepare(...);assert(a);TestWorld.artifactIndex=6;return a,t,r
          end''')
        self.c.RunNow()
        self.assertEqual((len(self.w.choiceRequests), self.entry().stage), (0, 'CHOICE_ARMED'), self.logs)
        self.w.artifactIndex = 5
        self.reload()
        self.w.turn += 1
        self.c.RunNow()
        self.assertEqual(len(self.w.choiceRequests), 0)

    def test_absent_queue_or_unconfirmed_permission_never_creates_choice(self):
        for mutation in ('TestWorld.pendingArtifact=false', 'TestArchBridge.allowWrite=false',
                         'ExposedMembers.BaiqiArchaeologyBridge.PreparePendingChoice=nil'):
            with self.subTest(mutation=mutation):
                self.setUp()
                self.lua.execute(mutation)
                self.c.RunNow()
                self.assertEqual((len(self.w.choiceRequests), len(self.w.archRequests)), (0, 0), self.logs)
                self.w.queueSize = 0
                self.c.RefreshProduction()
                self.c.RunNow()
                self.assertEqual(len(self.w.cityRequests), 1, self.logs)

    def test_observed_prior_operation_never_becomes_new_pending_migration(self):
        self.w.pendingArtifact, self.w.missionaryMoves, self.w.archResource = False, 4, 9
        self.w.autoExcavate, self.w.autoChoice = True, True
        self.c.RunNow()
        self.c.RunNow()
        self.assertEqual(self.entry().stage, 'OBSERVED')
        self.w.pendingArtifact, self.w.artifactIndex = True, 6
        self.c.RunNow()
        self.assertEqual((len(self.w.choiceRequests), self.h.store[KEY].serial), (1, 1), self.logs)
        self.assertIsNone(self.entry().legacy)


if __name__ == '__main__':
    unittest.main()
