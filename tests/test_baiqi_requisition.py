"""Fault injection runs the actual quotation and paid-transfer backend in Lua 5.3."""
from pathlib import Path
import unittest
from lupa.lua53 import LuaRuntime

ROOT = Path(__file__).resolve().parents[1]


class RequisitionTests(unittest.TestCase):
    def setUp(self):
        self.lua = LuaRuntime(unpack_returned_tuples=True)
        self.lua.execute((ROOT / 'tests/lua/mock_requisition.lua').read_text(encoding='utf-8'))
        for name in ('BaiqiConfig', 'BaiqiPolicy', 'BaiqiPlanner', 'BaiqiRights', 'BaiqiRequisition', 'BaiqiCapture'):
            self.lua.execute((ROOT / f'mod/Baiqi/Lua/{name}.lua').read_text(encoding='utf-8'))
        self.g = self.lua.globals()
        self.w = self.g.TestCapture
        self.backend = self.g.BaiqiCapture

    def test_success_and_duplicate_have_single_correlated_transfer_payment_action(self):
        params = self.g.TestParams()
        self.assertEqual(self.backend.Request(7, params), (True, 'committed'))
        self.assertEqual((self.w.owner, self.w.gold, self.w.moves), (7, 600, 0))
        self.assertEqual(self.backend.Request(7, params), (True, 'duplicate'))
        self.assertEqual((self.w.transferCalls, self.w.charges, self.w.finishCalls), (1, 1, 1))
        self.assertEqual(self.w.props['BAIQI_REQUISITION_V1'].operations[params.requestID].stage, 'COMMITTED')

    def test_validation_and_cancel_do_not_spend_anything(self):
        params = self.g.TestParams()
        params.confirmed = False
        self.assertEqual(self.backend.Request(7, params), (False, 'not_confirmed'))
        params.confirmed, self.w.atWar = True, False
        self.assertEqual(self.backend.Request(7, params), (False, 'not_at_war'))
        self.assertEqual((self.w.transferCalls, self.w.charges, self.w.finishCalls), (0, 0, 0))

    def granary_params(self):
        quote, reason = self.g.BaiqiRequisition.Quote(7, 9, 3, 12, 'granary')
        self.assertIsNotNone(quote, reason)
        quote.confirmed = True
        quote.requestID = self.g.BaiqiRequisition.RequestID(quote)
        return quote

    def test_independent_granary_grants_real_properties_with_no_city_transfer(self):
        self.w.damage = 0  # Building rights need broken outer defense, not low garrison HP.
        params = self.granary_params()
        self.assertEqual(self.backend.Request(7, params), (True, 'committed'))
        self.assertEqual((self.w.owner, self.w.granary, self.w.gold, self.w.moves), (3, True, 850, 0))
        self.assertEqual(self.w.sourceProps['BAIQI_GRANARY_OUT'], 1)
        self.assertEqual(self.w.recipientProps['BAIQI_GRANARY_IN'], 1)
        self.assertEqual(self.backend.Request(7, params), (True, 'duplicate'))
        self.assertEqual((self.w.transferCalls, self.w.charges, self.w.finishCalls), (0, 1, 1))

    def test_rights_pillage_suspend_repair_resume_and_capture_end_without_more_fees(self):
        self.backend.Request(7, self.granary_params())
        self.w.pillaged = True
        self.g.BaiqiRights.Refresh()
        self.assertEqual((self.w.sourceProps['BAIQI_GRANARY_OUT'], self.w.recipientProps['BAIQI_GRANARY_IN']), (0, 0))
        self.w.pillaged = False
        self.g.BaiqiRights.Refresh()
        self.assertEqual(self.w.recipientProps['BAIQI_GRANARY_IN'], 1)
        self.w.owner = 7
        self.g.BaiqiRights.Refresh()
        self.assertEqual((self.w.sourceProps['BAIQI_GRANARY_OUT'], self.w.recipientProps['BAIQI_GRANARY_IN']), (0, 0))
        self.assertEqual(self.w.gameProps['BAIQI_RIGHTS_V1'].leases['100'].status, 'EXPIRED')
        self.assertEqual((self.w.charges, self.w.finishCalls), (1, 1))

    def test_rights_reload_refresh_is_idempotent_and_cannot_stack_benefits(self):
        self.backend.Request(7, self.granary_params())
        for _ in range(4):
            self.g.BaiqiRights.Refresh()
            self.backend.Recover(7)
        self.assertEqual(self.w.recipientProps['BAIQI_GRANARY_IN'], 1)
        self.assertEqual((self.w.charges, self.w.finishCalls), (1, 1))

    def test_unsupported_modified_building_and_missing_granary_are_rejected(self):
        params = self.granary_params()
        self.w.extraModifier = True
        self.assertEqual(self.backend.Request(7, params), (False, 'building_profile_unsupported'))
        self.w.extraModifier, self.w.granary = False, False
        self.assertEqual(self.backend.Request(7, params), (False, 'no_operating_granary'))
        self.assertEqual((self.w.charges, self.w.transferCalls, self.w.finishCalls), (0, 0, 0))

    def test_changed_recipient_does_not_silently_redirect_paid_building(self):
        params = self.granary_params()
        params.recipientIndex = 999
        self.assertEqual(self.backend.Request(7, params), (False, 'quote_changed'))
        self.assertIsNone(self.w.sourceProps['BAIQI_GRANARY_OUT'])
        self.assertEqual(self.w.charges, 0)

    def test_corrupt_rights_ledger_disables_orphan_effects_without_regranting(self):
        self.backend.Request(7, self.granary_params())
        self.w.gameProps['BAIQI_RIGHTS_V1'].version = 999
        self.assertFalse(self.g.BaiqiRights.Refresh())
        self.assertEqual((self.w.sourceProps['BAIQI_GRANARY_OUT'], self.w.recipientProps['BAIQI_GRANARY_IN']), (0, 0))
        self.assertEqual((self.w.charges, self.w.finishCalls), (1, 1))

    def test_requoted_cost_population_turn_and_visibility_reject_changes(self):
        params = self.g.TestParams()
        self.w.population = 3
        self.assertEqual(self.backend.Request(7, params), (False, 'quote_changed'))
        self.w.population, self.w.visible = 2, False
        self.assertEqual(self.backend.Request(7, params), (False, 'not_visible'))
        self.w.visible, self.w.turn = True, 9
        self.assertEqual(self.backend.Request(7, params), (False, 'stale_turn'))
        self.assertEqual((self.w.transferCalls, self.w.charges, self.w.finishCalls), (0, 0, 0))

    def test_ambiguous_transfer_is_frozen_and_never_replayed_or_refunded(self):
        params = self.g.TestParams()
        self.w.throwAfterTransfer = True
        self.assertEqual(self.backend.Request(7, params), (False, 'transfer_unresolved'))
        self.assertEqual(self.w.owner, 7)
        self.assertEqual((self.w.charges, self.w.finishCalls), (0, 0))
        self.assertEqual(self.backend.Request(7, params), (False, 'duplicate'))
        self.assertEqual(self.w.transferCalls, 1)
        self.backend.Recover(7)
        self.assertEqual(self.w.props['BAIQI_REQUISITION_V1'].operations[params.requestID].stage, 'UNKNOWN')

    def test_payment_error_after_transfer_freezes_without_second_payment(self):
        params = self.g.TestParams()
        self.w.failCharge = True
        self.assertEqual(self.backend.Request(7, params), (False, 'charge_unresolved'))
        self.w.failCharge = False
        self.assertEqual(self.backend.Request(7, params), (False, 'duplicate'))
        self.assertEqual((self.w.transferCalls, self.w.charges, self.w.finishCalls), (1, 1, 0))

    def test_saved_midstage_record_recovers_unknown_without_inferring_from_owner(self):
        self.lua.execute("""
          local q=TestParams()
          TestCapture.props.BAIQI_REQUISITION_V1={version=1,operations={
            [q.requestID]={id=q.requestID,stage='SUBMITTED',phase='CHARGING',unitID=9,x=3,y=2}}}
          TestCapture.owner=7
        """)
        self.backend.Recover(7)
        journal = self.w.props['BAIQI_REQUISITION_V1']
        records = list(journal.operations.values())
        self.assertEqual(records[0].stage, 'UNKNOWN')
        self.assertEqual((self.w.transferCalls, self.w.charges, self.w.finishCalls), (0, 0, 0))

    def test_unknown_conflicts_and_corrupt_duplicate_fail_closed(self):
        params = self.g.TestParams()
        self.lua.execute("""
          TestCapture.props.BAIQI_REQUISITION_V1={version=1,operations={
            older={id='older',stage='UNKNOWN',unitID=9,x=8,y=8}}}
        """)
        self.assertEqual(self.backend.Request(7, params), (False, 'pending_operation'))
        self.w.props['BAIQI_REQUISITION_V1'].operations[params.requestID] = 42
        self.assertEqual(self.backend.Request(7, params), (False, 'journal_corrupt'))
        self.assertEqual(self.w.transferCalls, 0)

    def test_escort_healthy_city_walls_and_poor_treasury_fail_without_effects(self):
        params = self.g.TestParams()
        for field, invalid, restored, reason in (
            ('formation', 2, 1, 'formation'), ('damage', 0, 150, 'city_healthy'),
            ('outer', 100, 0, 'walls_remaining'), ('gold', 399, 1000, 'insufficient_gold')):
            with self.subTest(reason=reason):
                setattr(self.w, field, invalid)
                self.assertEqual(self.backend.Request(7, params), (False, reason))
                setattr(self.w, field, restored)
        self.assertEqual((self.w.transferCalls, self.w.charges, self.w.finishCalls), (0, 0, 0))


if __name__ == '__main__':
    unittest.main()
