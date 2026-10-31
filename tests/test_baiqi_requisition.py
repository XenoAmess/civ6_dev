"""Fault injection runs the actual quotation and paid-transfer backend in Lua 5.3."""
from pathlib import Path
import unittest
from lupa.lua53 import LuaRuntime

ROOT = Path(__file__).resolve().parents[1]


class RequisitionTests(unittest.TestCase):
    def setUp(self):
        self.lua = LuaRuntime(unpack_returned_tuples=True)
        self.lua.execute((ROOT / 'tests/lua/mock_requisition.lua').read_text(encoding='utf-8'))
        for name in ('BaiqiConfig', 'BaiqiPolicy', 'BaiqiPlanner', 'BaiqiRequisition', 'BaiqiCapture'):
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


    def test_withdrawn_granary_request_is_rejected_before_legacy_duplicate(self):
        params = self.g.TestParams()
        params.kind, params.requestID = 'granary', 'granary:old'
        self.lua.execute("TestCapture.props.BAIQI_REQUISITION_V1={version=1,operations={['granary:old']={stage='COMMITTED'}}}")
        self.assertEqual(self.backend.Request(7, params), (False, 'invalid_target'))
        self.assertEqual((self.w.transferCalls, self.w.charges, self.w.finishCalls), (0, 0, 0))

    def test_removed_rights_migration_clears_effects_and_flags_without_payment(self):
        self.lua.execute("""
          TestCapture.sourceProps.BAIQI_GRANARY_OUT=1
          TestCapture.recipientProps.BAIQI_GRANARY_IN=1
          TestCapture.gameProps.BAIQI_RIGHTS_V1={version=1}
          TestCapture.props.BAIQI_STATE_V1={enabled=false,protected={100}}
          PlayerManager={GetAliveIDs=function() return {7} end}
          TestEvents={}
          GameEvents=setmetatable({},{__index=function(t,key)
            local event={Add=function(fn) TestEvents[key]=fn end};rawset(t,key,event);return event
          end})
        """)
        self.lua.execute((ROOT / 'mod/Baiqi/Lua/BaiqiGameplay.lua').read_text(encoding='utf-8'))
        for _ in range(2):
            self.g.TestEvents.OnGameTurnStarted()
        self.assertEqual(self.w.sourceProps.BAIQI_GRANARY_OUT, 0)
        self.assertEqual(self.w.recipientProps.BAIQI_GRANARY_IN, 0)
        self.assertIsNone(self.w.gameProps.BAIQI_RIGHTS_V1)
        self.assertIsNone(self.w.props.BAIQI_STATE_V1)
        self.assertEqual((self.w.gold, self.w.moves, self.w.transferCalls, self.w.charges), (1000, 2, 0, 0))


if __name__ == '__main__':
    unittest.main()
