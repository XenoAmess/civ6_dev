"""Player confirmation boundaries for the actual UI module."""
from pathlib import Path
import unittest
from lupa.lua53 import LuaRuntime

ROOT = Path(__file__).resolve().parents[1]


class ManualActionTests(unittest.TestCase):
    def setUp(self):
        self.lua = LuaRuntime(unpack_returned_tuples=True)
        self.lua.execute((ROOT / 'tests/lua/mock_requisition.lua').read_text(encoding='utf-8'))
        for name in ('BaiqiConfig', 'BaiqiPolicy', 'BaiqiRights', 'BaiqiRequisition'):
            self.lua.execute((ROOT / f'mod/Baiqi/Lua/{name}.lua').read_text(encoding='utf-8'))
        self.lua.globals().TestUI()
        self.lua.execute((ROOT / 'mod/Baiqi/Lua/BaiqiActions.lua').read_text(encoding='utf-8'))
        self.g = self.lua.globals()
        self.w, self.actions = self.g.TestCapture, self.g.BaiqiActions

    def test_quote_cancel_and_reopen_never_submit_before_explicit_confirmation(self):
        self.actions.Show('granary')
        self.assertTrue(self.w.opened)
        self.assertIn('150', self.w.popupText)
        self.assertIn('Recipient', self.w.popupText)
        self.assertEqual(len(self.w.requests), 0)
        self.w.cancel()
        self.actions.Show('city')
        self.assertIn('400', self.w.popupText)
        self.assertEqual(len(self.w.requests), 0)

    def test_confirmation_sends_one_bound_quote_and_blocks_double_open(self):
        self.actions.Show('granary')
        self.w.confirm()
        self.actions.Show('granary')
        self.assertEqual(len(self.w.requests), 1)
        request = self.w.requests[1]
        self.assertEqual((request.OnStart, request.kind, request.confirmed), ('BaiqiRequisition', 'granary', True))
        self.assertEqual((request.cost, request.recipientCityID, request.recipientIndex), (150, 20, 200))

    def test_changed_state_at_confirmation_and_hidden_target_do_not_submit(self):
        self.actions.Show('city')
        self.w.moves = 0
        self.w.confirm()
        self.assertEqual(len(self.w.requests), 0)
        self.w.moves, self.w.visible, self.w.opened = 2, False, False
        self.actions.Show('city')
        self.assertFalse(self.w.opened)
        self.assertEqual(len(self.w.requests), 0)

    def test_result_is_read_from_gameplay_record_and_recovery_is_once_per_turn(self):
        self.actions.Recover()
        self.actions.Recover()
        self.assertEqual(len(self.w.requests), 1)
        self.actions.Show('city')
        self.w.confirm()
        request = self.w.requests[2]
        self.w.props['BAIQI_REQUISITION_RESULT'] = self.lua.table_from(
            {'id': request.requestID, 'stage': 'REJECTED', 'reason': 'quote_changed'})
        self.assertIn('未执行', self.actions.Status())
        self.actions.Show('city')
        self.assertTrue(self.w.opened)


if __name__ == '__main__':
    unittest.main()
