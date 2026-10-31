"""Exercise map interaction, including deferred native attack coordinates."""
from pathlib import Path
import unittest
from lupa.lua53 import LuaRuntime

ROOT = Path(__file__).resolve().parents[1]


class MapActionTests(unittest.TestCase):
    def setUp(self):
        self.lua = LuaRuntime(unpack_returned_tuples=True)
        self.lua.execute((ROOT / 'tests/lua/mock_requisition.lua').read_text(encoding='utf-8'))
        self.g = self.lua.globals()
        self.g.TestUI()
        def include(name):
            if name == 'PopupDialog':  # Native popup API is the controlled UI double.
                return
            source = ROOT / f'mod/Baiqi/Lua/{name}.lua'
            self.lua.execute(source.read_text(encoding='utf-8'))
        self.g.include = include
        self.lua.execute('TestMove=function(u,x,y) TestCapture.nativeMove={unit=u:GetID(),x=x,y=y} end')
        self.lua.execute((ROOT / 'mod/Baiqi/Lua/BaiqiActions.lua').read_text(encoding='utf-8'))
        self.w, self.actions = self.g.TestCapture, self.g.BaiqiActions
        self.unit = self.g.UI.GetHeadSelectedUnit()

    def interact(self):
        return self.actions.Interact(self.unit, 3, 2, self.g.TestMove)

    def test_cancel_has_no_request_payment_or_native_attack(self):
        self.assertTrue(self.interact())
        self.assertIn('400', self.w.popupText)
        self.assertEqual(len(self.w.requests), 0)
        self.w.cancel()
        self.assertEqual((self.w.gold, self.w.moves, self.w.transferCalls), (1000, 2, 0))
        self.assertIsNone(self.w.nativeMove)

    def test_confirm_binds_city_quote_and_prevents_double_submission(self):
        self.interact()
        self.w.confirm()
        self.interact()
        self.assertEqual(len(self.w.requests), 1)
        request = self.w.requests[1]
        self.assertEqual((request.OnStart, request.kind, request.cost, request.confirmed), ('BaiqiRequisition', 'city', 400, True))
        self.assertIsNone(self.w.nativeMove)

    def test_normal_attack_uses_original_coordinates_and_fresh_unit(self):
        self.interact()
        self.lua.execute('UI.GetCursorPlotCoord=function() return 99,98 end')
        self.w.normalAttack()
        self.assertEqual((self.w.nativeMove.unit, self.w.nativeMove.x, self.w.nativeMove.y), (9, 3, 2))
        self.assertEqual(len(self.w.requests), 0)

    def test_target_changed_or_invisible_cannot_submit(self):
        self.interact()
        self.w.population = 4
        self.w.confirm()
        self.assertEqual(len(self.w.requests), 0)
        self.w.population, self.w.visible, self.w.opened = 2, False, False
        self.assertFalse(self.interact())
        self.assertFalse(self.w.opened)

    def test_popup_confirm_and_normal_attack_do_not_retarget_recycled_unit_slot(self):
        self.interact()
        self.w.unitID = 65545
        self.w.confirm()
        self.assertEqual(len(self.w.requests), 0)
        self.w.unitID = None
        self.interact()
        self.w.unitID = 65545
        self.w.normalAttack()
        self.assertIsNone(self.w.nativeMove)
        self.assertEqual((self.w.gold, self.w.moves, self.w.transferCalls), (1000, 2, 0))

    def test_ineligible_map_target_preserves_native_move(self):
        move = self.actions.WrapMove(self.g.TestMove)
        self.w.damage = 0
        move(self.unit, 3, 2)
        self.assertEqual((self.w.nativeMove.x, self.w.nativeMove.y), (3, 2))
        self.assertEqual(len(self.w.requests), 0)

    def test_result_notice_reads_gameplay_receipt(self):
        self.interact()
        self.w.confirm()
        self.w.props.BAIQI_REQUISITION_RESULT = self.lua.table_from({'id': self.w.requests[1].requestID, 'stage': 'REJECTED'})
        self.actions.Poll()
        self.assertIn('未执行', self.w.popupText)

    def test_other_leader_uses_native_city_move_without_popup(self):
        self.w.leader = 'LEADER_TRAJAN'
        self.actions.WrapMove(self.g.TestMove)(self.unit, 3, 2)
        self.assertEqual((self.w.nativeMove.x, self.w.nativeMove.y), (3, 2))
        self.assertIsNone(self.w.opened)
        self.assertEqual(len(self.w.requests), 0)

    def test_guarded_civilian_cannot_enter_native_map_move(self):
        self.lua.execute('BaiqiUIGuard={Civilian=function() return true end}')
        self.assertFalse(self.actions.WrapMove(self.g.TestMove)(self.unit, 3, 2))
        self.assertIsNone(self.w.nativeMove)
        self.assertEqual(len(self.w.requests), 0)


if __name__ == '__main__':
    unittest.main()
