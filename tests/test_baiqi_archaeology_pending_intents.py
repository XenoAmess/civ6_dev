import unittest
from archaeology_intent_harness import ROOT, KEY, archaeology_runtime


class ArchaeologyPendingIntentTests(unittest.TestCase):
    def setUp(self):
        self.lua, self.module, self.h = archaeology_runtime()
        self.lua.execute('''H.pendingProposal=H.Copy(H.proposal)
          H.pendingProposal.resourceIndex=nil;H.pendingProposal.resourceType=nil''')

    def prepare(self):
        return self.module.bridge.PreparePendingChoice(7, 4, self.h.pendingProposal, self.h.descriptor)

    def entry(self):
        return self.h.store[KEY].operations['4']

    def test_pending_choice_persists_without_fabricating_resource_or_excavation(self):
        self.h.moves, self.h.resourceIndex, self.h.siteOwner = 0, -1, 8
        granted, token, _ = self.prepare()
        self.assertTrue(granted)
        self.assertEqual((token, self.entry().stage, self.entry().legacy), ('archaeology:7:1', 'CHOICE_ARMED', True))
        self.assertIsNone(self.entry().resourceIndex)
        self.assertIsNone(self.entry().resourceType)
        self.assertEqual((self.h.resourceReads, self.h.writes), (0, 1))

    def test_prior_operations_at_any_stage_never_receive_pending_migration(self):
        for stage in ('EXCAVATE_ARMED', 'CHOICE_ARMED', 'OBSERVED'):
            with self.subTest(stage=stage):
                self.setUp()
                self.assertTrue(self.module.bridge.PrepareExcavation(7, 4, self.h.proposal)[0])
                if stage != 'EXCAVATE_ARMED':
                    self.assertTrue(self.module.bridge.PrepareChoice(7, 4, 'archaeology:7:1', self.h.descriptor)[0])
                if stage == 'OBSERVED':
                    self.assertTrue(self.module.ObserveCreated(7, 4, 2, 3, 24, 101))
                writes = self.h.writes
                self.assertFalse(self.prepare()[0])
                self.assertEqual(self.h.writes, writes)

    def test_unresolved_other_unit_blocks_new_pending_permission(self):
        self.h.unitID = 5
        self.assertTrue(self.module.bridge.PrepareExcavation(7, 5, self.h.proposal)[0])
        self.h.unitID = 4
        self.assertFalse(self.prepare()[0])
        self.assertEqual(self.h.store[KEY].serial, 1)

    def test_exact_packets_descriptor_and_owned_home_are_required(self):
        for mutation in ('H.pendingProposal.resourceIndex=9', 'H.pendingProposal.extra=true',
                         'H.descriptor.homeCityID=67', 'H.descriptor.unitID=5',
                         'H.descriptor.choicePlayerID=3', 'H.cityOwner=8',
                         'H.formation=2', 'H.visible=false', 'H.active=false'):
            with self.subTest(mutation=mutation):
                self.setUp()
                self.lua.execute(mutation)
                self.assertFalse(self.prepare()[0])
                self.assertEqual(self.h.writes, 0)

    def test_final_fact_reads_recheck_current_visibility(self):
        self.lua.execute('''H.formationReads=0
          H.unit.GetFormationUnitCount=function()
            H.formationReads=H.formationReads+1
            if H.formationReads==2 then H.visible=false end
            return 1
          end''')
        self.assertFalse(self.prepare()[0])
        self.assertEqual(self.h.writes, 0)

    def test_persists_to_player_returned_by_last_fresh_fact_check(self):
        self.lua.execute('''
          H.secondStore={};H.secondWrites=0
          local second={};for k,v in pairs(H.player) do second[k]=v end
          second.GetProperty=function(_,key) return H.Copy(H.secondStore[key]) end
          second.SetProperty=function(_,key,value) H.secondWrites=H.secondWrites+1;H.secondStore[key]=H.Copy(value) end
          H.visibleReads=0
          H.visibility.IsVisible=function()
            H.visibleReads=H.visibleReads+1
            if H.visibleReads==1 then Players[7]=second end
            return true
          end
        ''')
        self.assertTrue(self.prepare()[0])
        self.assertEqual((self.h.writes, self.h.secondWrites), (0, 1))
        self.assertIsNone(self.h.store[KEY])
        self.assertEqual(self.h.secondStore[KEY].operations['4'].stage, 'CHOICE_ARMED')

    def test_corrupt_unreadable_or_unconfirmed_property_never_grants(self):
        for mutation in ('H.store.BAIQI_ARCHAEOLOGY_INTENTS_V1={version=99}',
                         'H.throwRead=true', 'H.allowWrite=false'):
            with self.subTest(mutation=mutation):
                self.setUp()
                self.lua.execute(mutation)
                self.assertFalse(self.prepare()[0])

    def test_written_unknown_choice_survives_core_reload_and_is_never_regranted(self):
        self.h.writeThenThrow = True
        self.assertFalse(self.prepare()[0])
        self.assertEqual(self.entry().stage, 'CHOICE_ARMED')
        self.h.writeThenThrow = False
        self.module = self.lua.execute((ROOT / 'mod/Baiqi/Lua/BaiqiArchaeologyIntentGameplay.lua').read_text(encoding='utf-8'))
        self.assertFalse(self.prepare()[0])
        self.assertEqual((self.h.writes, self.entry().token), (1, 'archaeology:7:1'))

    def test_actual_receipt_consumer_can_settle_consumed_legacy_unit_once(self):
        self.assertTrue(self.prepare()[0])
        self.h.unitExists, self.h.active = False, False
        self.assertTrue(self.module.ObserveCreated(7, 4, 2, 3, 24, 101))
        self.assertEqual((self.entry().stage, self.entry().newWorkID), ('OBSERVED', 101))
        self.assertFalse(self.module.ObserveCreated(7, 4, 2, 3, 24, 101))
        self.assertEqual(self.h.writes, 2)


if __name__ == '__main__':
    unittest.main()
