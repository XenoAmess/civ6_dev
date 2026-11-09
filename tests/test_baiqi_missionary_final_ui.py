"""Actual Controller consumes trusted Core completion for an exhausted unit."""
import unittest
import test_baiqi_missionary as missionary

class FinalChargeUITests(unittest.TestCase):
    def setUp(self):
        self.base=missionary.MissionaryTests();self.base.setUp()

    def tearDown(self):self.base.tearDown()

    def test_last_unit_missing_clears_once_only_after_matching_core_receipt(self):
        b=self.base;b.w.spreadCharges=1;b.c.RunNow()
        b.w.withMissionary=False;b.lua.execute("TestRelBridge.store.BAIQI_RELIGIOUS_INTENTS_V1.operations['4'].stage='OBSERVED'")
        b.c.RunNow();b.c.RunNow()
        self.assertEqual(sum('proof=core_final_charge_receipt'in s for s in b.logs),1)
        self.assertEqual(len(b.w.spreadRequests),1)

    def test_missing_with_armed_or_foreign_token_or_nonfinal_charge_does_not_clear(self):
        for case in ('ARMED','foreign-token','nonfinal'):
            with self.subTest(case=case):
                self.setUp();b=self.base;b.w.spreadCharges=3 if case=='nonfinal'else 1;b.c.RunNow()
                b.w.withMissionary=False
                if case!='ARMED':b.lua.execute("TestRelBridge.store.BAIQI_RELIGIOUS_INTENTS_V1.operations['4'].stage='OBSERVED'")
                if case=='foreign-token':b.lua.execute("ExposedMembers.BaiqiReligiousIntentBridge.Inspect=function()return 'OBSERVED','wrong' end")
                b.c.RunNow();b.c.RunNow()
                self.assertFalse(any('proof=core_final_charge_receipt'in s for s in b.logs))
                self.assertEqual(len(b.w.spreadRequests),1)

if __name__=='__main__':unittest.main()
