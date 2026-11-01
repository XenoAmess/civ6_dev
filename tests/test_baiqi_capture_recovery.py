"""Interrupt actual transaction functions; recover genuine receipts, never guessed effects."""
from pathlib import Path
import unittest
from lupa.lua53 import LuaRuntime

ROOT = Path(__file__).resolve().parents[1]


class CaptureRecoveryTests(unittest.TestCase):
    def setUp(self):
        self.lua = LuaRuntime(unpack_returned_tuples=True)
        self.lua.execute((ROOT/'tests/lua/mock_requisition.lua').read_text(encoding='utf-8'))
        for name in ('BaiqiConfig', 'BaiqiPolicy', 'BaiqiPlanner', 'BaiqiRequisition', 'BaiqiCapture'):
            self.load(name)
        self.g, self.w = self.lua.globals(), self.lua.globals().TestCapture
        self.c = self.g.BaiqiCapture
        self.params = self.g.TestParams()

    def load(self, name):
        self.lua.execute((ROOT/f'mod/Baiqi/Lua/{name}.lua').read_text(encoding='utf-8'))

    def record(self):
        return self.w.props.BAIQI_REQUISITION_V1.operations[self.params.requestID]

    def inject(self, phase):
        self.lua.execute('''
local phase=...
local name=phase=='TRANSFERRED' and 'Number' or 'MatchesID'
local original=BaiqiPolicy[name]
BaiqiPolicy[name]=function(...)
 local j=TestCapture.props.BAIQI_REQUISITION_V1
 local r=j and j.lastID and j.operations[j.lastID]
 if r and r.phase==phase then
  BaiqiPolicy[name]=original
  error('one-shot after actual persisted '..phase)
 end
 return original(...)
end
''', phase)

    def partial(self, phase):
        self.inject(phase)
        self.assertEqual(self.c.Request(7, self.params), (False, 'execution_interrupted'))
        self.assertEqual((self.record().stage, self.record().phase), ('UNKNOWN', phase))

    def test_actual_transferred_receipt_without_balance_fields_resumes_once_after_module_reload(self):
        self.partial('TRANSFERRED')
        self.assertIsNone(self.record().balanceBefore)
        self.assertEqual((self.w.owner, self.w.gold, self.w.moves), (7, 1000, 2))
        self.load('BaiqiCapture')
        self.g.BaiqiCapture.Recover(7)
        self.g.BaiqiCapture.Recover(7)
        self.assertEqual((self.w.gold, self.w.moves, self.w.transferCalls, self.w.charges, self.w.finishCalls), (600, 0, 1, 1, 1))
        self.assertEqual((self.record().stage, self.record().phase), ('COMMITTED', 'DONE'))
        self.assertEqual(self.w.props.BAIQI_REQUISITION_RESULT.stage, 'COMMITTED')

    def test_actual_charged_receipt_does_not_charge_again_despite_unrelated_gold_change(self):
        self.partial('CHARGED')
        self.assertEqual((self.record().chargeObserved, self.record().balanceBefore, self.record().balanceAfter), (True, 1000, 600))
        self.w.gold = 650
        self.c.Recover(7)
        self.c.Recover(7)
        self.assertEqual((self.w.gold, self.w.moves, self.w.charges, self.w.finishCalls), (650, 0, 1, 1))

    def test_native_finish_applied_then_raised_commits_without_another_finish_or_charge(self):
        self.lua.execute('''
local finish=UnitManager.FinishMoves
UnitManager.FinishMoves=function(unit)
 UnitManager.FinishMoves=finish;finish(unit);error('after actual movement exhaustion')
end
''')
        self.assertEqual(self.c.Request(7, self.params), (False, 'movement_unresolved'))
        self.assertEqual((self.record().phase, self.w.moves), ('FINISHING', 0))
        self.c.Recover(7)
        self.assertEqual((self.record().stage, self.w.charges, self.w.finishCalls), ('COMMITTED', 1, 1))

    def test_finish_not_started_can_resume_same_turn_without_second_debit(self):
        self.lua.execute('''
local finish=UnitManager.FinishMoves
UnitManager.FinishMoves=function() UnitManager.FinishMoves=finish;error('before movement exhaustion') end
''')
        self.c.Request(7, self.params)
        self.assertEqual((self.record().phase, self.w.moves, self.w.finishCalls), ('FINISHING', 2, 0))
        self.c.Recover(7)
        self.assertEqual((self.record().stage, self.w.charges, self.w.finishCalls), ('COMMITTED', 1, 1))

    def test_unknown_debit_is_not_inferred_from_matching_balance(self):
        self.lua.execute('''
local treasury=TestCapture.objects.player:GetTreasury();local charge=treasury.ChangeGoldBalance
treasury.ChangeGoldBalance=function(self,value) charge(self,value);error('debit result not returned') end
''')
        self.assertEqual(self.c.Request(7, self.params), (False, 'charge_unresolved'))
        self.assertEqual((self.record().phase, self.w.gold), ('CHARGING', 600))
        self.c.Recover(7)
        self.assertEqual((self.record().stage, self.w.gold, self.w.charges, self.w.finishCalls), ('UNKNOWN', 600, 1, 0))

    def test_later_third_party_owner_change_is_not_transfer_receipt(self):
        self.w.failTransfer = True
        self.c.Request(7, self.params)
        self.w.owner = 7  # Independent external ownership change after failed call.
        self.c.Recover(7)
        self.assertEqual((self.record().stage, self.record().phase), ('UNKNOWN', 'TRANSFERRING'))
        self.assertEqual((self.w.charges, self.w.finishCalls), (0, 0))

    def test_changed_turn_identity_owner_formation_or_local_player_keeps_receipt_frozen(self):
        for field, value in (('turn', 9), ('unitID', 65545), ('cityID', 65548),
                             ('owner', 3), ('formation', 2), ('localPlayer', 3), ('active', False)):
            with self.subTest(field=field):
                self.setUp(); self.partial('TRANSFERRED')
                self.w[field] = value
                self.c.Recover(7)
                self.assertEqual(self.record().stage, 'UNKNOWN')
                self.assertEqual((self.w.gold, self.w.charges, self.w.finishCalls), (1000, 0, 0))

    def test_invalid_cost_id_charge_receipt_or_conflicting_record_does_not_settle(self):
        for case in ('cost', 'id', 'charge', 'conflict', 'quoted'):
            with self.subTest(case=case):
                self.setUp(); self.partial('CHARGED' if case=='charge' else 'TRANSFERRED')
                if case == 'cost':
                    self.record().cost = 1
                elif case == 'id':
                    self.record().id = 'forged'
                elif case == 'charge':
                    self.record().balanceAfter = 999
                elif case == 'quoted':
                    self.record().stage = 'QUOTED'
                else:
                    self.lua.execute("TestCapture.props.BAIQI_REQUISITION_V1.operations.other={id='other',stage='UNKNOWN',unitID=9}")
                before = self.w.gold, self.w.charges
                self.c.Recover(7)
                self.assertNotEqual(self.record().stage, 'COMMITTED')
                self.assertEqual((self.w.gold, self.w.charges), before)
                self.assertEqual(self.w.finishCalls, 0)

    def test_insufficient_funds_waits_then_pays_once_when_restored(self):
        self.partial('TRANSFERRED')
        self.w.gold = 399
        self.c.Recover(7)
        self.assertEqual((self.w.charges, self.record().phase), (0, 'TRANSFERRED'))
        self.w.gold = 401
        self.c.Recover(7); self.c.Recover(7)
        self.assertEqual((self.w.gold, self.w.charges, self.w.moves), (1, 1, 0))

    def test_fault_during_recovery_keeps_new_definite_phase_and_never_redebits(self):
        self.partial('TRANSFERRED')
        self.inject('CHARGED')
        self.c.Recover(7)
        self.assertEqual((self.record().stage, self.record().phase, self.w.charges), ('UNKNOWN', 'CHARGED', 1))
        self.c.Recover(7)
        self.assertEqual((self.record().stage, self.w.charges, self.w.finishCalls), ('COMMITTED', 1, 1))

    def test_new_turn_started_during_debit_never_exhausts_its_movement(self):
        self.partial('TRANSFERRED')
        self.lua.execute('''
local treasury=TestCapture.objects.player:GetTreasury();local charge=treasury.ChangeGoldBalance
treasury.ChangeGoldBalance=function(self,value) charge(self,value);TestCapture.turn=9 end
''')
        self.c.Recover(7)
        self.assertEqual((self.record().stage, self.record().phase, self.w.charges, self.w.finishCalls), ('UNKNOWN', 'CHARGED', 1, 0))

    def test_gameplay_confirmed_handler_recovers_definite_interruption_without_user_retry(self):
        self.lua.execute('''
TestCapture.gameProps.BAIQI_WITHDRAWN_RIGHTS_CLEANED=2
TestHandlers={}
GameEvents=setmetatable({},{__index=function(t,key)
 local event={Add=function(fn) TestHandlers[key]=fn end};rawset(t,key,event);return event
end})
''')
        self.load('BaiqiGameplay')
        self.inject('TRANSFERRED')
        self.g.TestHandlers.BaiqiRequisition(7, self.params)
        self.assertEqual((self.w.gold, self.w.moves, self.w.charges, self.w.transferCalls), (600, 0, 1, 1))
        self.assertEqual(self.w.props.BAIQI_REQUISITION_RESULT.stage, 'COMMITTED')


if __name__ == '__main__':
    unittest.main()
