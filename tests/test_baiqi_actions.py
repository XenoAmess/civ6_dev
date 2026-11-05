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

    def flag_context(self):
        """Native bound handler looks up UnitManager when a flag is clicked."""
        include_original = self.g.include
        self.lua.execute('''
          TestCapture.nativeOperationCalls=0
          UnitOperationTypes={MOVE_TO=10,RANGE_ATTACK=11,PARAM_X='x',PARAM_Y='y'}
          UnitManager.RequestOperation=function(unit,operation,params,...)
            TestCapture.nativeOperationCalls=TestCapture.nativeOperationCalls+1
            TestCapture.lastOperation={unit=unit:GetID(),operation=operation,params=params,
              count=select('#',...),extra={...}}
            return 'native',nil,19
          end
          UnitManager.CanStartOperation=function(_,operation) return operation==10 end
          TestOriginalFlagManager=UnitManager
          function FlagEvent()
            local handlers={}
            return {Add=function(fn) handlers[fn]=true end,
              Remove=function(fn) handlers[fn]=nil end,
              Count=function() local n=0;for _ in pairs(handlers) do n=n+1 end;return n end,
              Fire=function() for fn in pairs(handlers) do fn() end end}
          end
          Events={GameCoreEventPlaybackComplete=FlagEvent()}
          ContextPtr={SetShutdown=function(_,fn) TestFlagShutdown=fn end}
          OnShutdown=function() TestCapture.nativeShutdown=true end
        ''')

        def include(name):
            if name == 'BaiqiUIGuard':
                self.lua.execute('BaiqiUIGuard={Civilian=function() return TestCapture.civilian==true end}')
            elif name == 'BaiqiUILoader':
                self.lua.execute('BaiqiUILoader={Load=function(name) include(name) end}')
            elif name == 'UnitFlagManager':
                # Relevant native path: both mouse buttons keep this handler;
                # the handler resolves the operation sink when invoked.
                self.lua.execute('''
                  function OnUnitFlagClick()
                    local selected=UI.GetHeadSelectedUnit()
                    local params={x=3,y=2,attack=true}
                    if UnitManager.CanStartOperation(selected,11,nil,params) then
                      UnitManager.RequestOperation(selected,11,params)
                    elseif UnitManager.CanStartOperation(selected,10,nil,params) then
                      UnitManager.RequestOperation(selected,10,params)
                    end
                  end
                  TestBoundFlagClick=OnUnitFlagClick
                ''')
            else:
                include_original(name)

        self.g.include = include
        self.lua.execute((ROOT / 'mod/Baiqi/UI/BaiqiUnitFlagManager.lua').read_text(encoding='utf-8'))
        self.actions = self.g.BaiqiActions
        return self.g.UnitManager.RequestOperation

    def test_flag_native_callback_defers_attack_until_player_chooses(self):
        self.flag_context()
        self.g.TestBoundFlagClick()
        self.assertEqual(self.w.nativeOperationCalls, 0)
        self.assertIn('400', self.w.popupText)
        self.assertEqual(len(self.w.requests), 0)
        self.w.confirm()
        self.assertEqual(len(self.w.requests), 1)
        self.assertEqual(self.w.nativeOperationCalls, 0)

    def test_flag_cancel_does_not_attack_or_pay(self):
        self.flag_context()
        self.g.TestBoundFlagClick()
        self.w.cancel()
        self.assertEqual((self.w.nativeOperationCalls, len(self.w.requests)), (0, 0))

    def test_flag_continue_preserves_operation_params_and_nil_varargs_once(self):
        request = self.flag_context()
        params = self.lua.table_from({'x': 3, 'y': 2, 'attack': True})
        request(self.unit, 11, params, 'intent', None, 7)
        self.assertEqual(self.w.nativeOperationCalls, 0)
        self.w.normalAttack()
        op = self.w.lastOperation
        self.assertEqual((op.unit, op.operation, op.params.x, op.params.y), (9, 11, 3, 2))
        self.assertEqual((op.count, op.extra[1], op.extra[2], op.extra[3]), (3, 'intent', None, 7))
        self.assertEqual((self.w.nativeOperationCalls, len(self.w.requests)), (1, 0))

    def test_flag_continue_cannot_retarget_mutated_params(self):
        request = self.flag_context()
        params = self.lua.table_from({'x': 3, 'y': 2})
        request(self.unit, 10, params)
        params.x = 4
        self.w.normalAttack()
        self.assertEqual(self.w.nativeOperationCalls, 0)

    def test_flag_unrelated_or_malformed_operations_preserve_native_return_shape(self):
        request = self.flag_context()
        for op, params in [(99, None), (10, None), (10, 'invalid'),
                           (10, {}), (10, {'x': '3', 'y': 2}),
                           (10, {'x': -1, 'y': 2}), (10, {'x': float('inf'), 'y': 2}),
                           (10, {'x': float('nan'), 'y': 2}), (10, {'x': 44, 'y': 2}),
                           (10, {'x': 3.5, 'y': 2}), (10, {'x': 3, 'y': 26})]:
            with self.subTest(operation=op, params=params):
                value = self.lua.table_from(params) if isinstance(params, dict) else params
                self.assertEqual(request(self.unit, op, value), ('native', None, 19))
        self.assertIsNone(self.w.opened)

    def test_flag_invisible_or_ineligible_or_noncity_target_preserves_attack(self):
        request = self.flag_context()
        params = self.lua.table_from({'x': 3, 'y': 2})
        self.w.visible = False
        self.assertEqual(request(self.unit, 10, params), ('native', None, 19))
        self.w.visible, self.w.damage = True, 0
        self.assertEqual(request(self.unit, 10, params), ('native', None, 19))
        self.w.damage = 150
        self.assertEqual(request(self.unit, 10, self.lua.table_from({'x': 4, 'y': 2})), ('native', None, 19))
        self.assertEqual(self.w.nativeOperationCalls, 3)
        self.assertIsNone(self.w.opened)

    def test_flag_other_leader_and_multiplayer_keep_native_operations(self):
        request = self.flag_context()
        params = self.lua.table_from({'x': 3, 'y': 2})
        self.w.leader = 'LEADER_TRAJAN'
        self.assertEqual(request(self.unit, 10, params), ('native', None, 19))
        self.w.leader = 'LEADER_BAIQI'
        self.lua.execute('GameConfiguration.IsAnyMultiplayer=function() return true end')
        self.assertEqual(request(self.unit, 10, params), ('native', None, 19))
        self.assertEqual(self.w.nativeOperationCalls, 2)
        self.assertIsNone(self.w.opened)

    def test_flag_civilian_remains_blocked(self):
        request = self.flag_context()
        self.w.civilian = True
        self.assertFalse(request(self.unit, 10, self.lua.table_from({'x': 3, 'y': 2})))
        self.assertEqual((self.w.nativeOperationCalls, len(self.w.requests)), (0, 0))

    def test_flag_pending_receipt_is_polled_and_shutdown_removes_binding(self):
        self.flag_context()
        self.assertEqual(self.g.Events.GameCoreEventPlaybackComplete.Count(), 1)
        self.g.TestBoundFlagClick()
        self.w.confirm()
        self.w.props.BAIQI_REQUISITION_RESULT = self.lua.table_from({
            'id': self.w.requests[1].requestID, 'stage': 'UNKNOWN'})
        self.g.Events.GameCoreEventPlaybackComplete.Fire()
        self.assertIn('冻结', self.w.popupText)
        self.g.TestFlagShutdown()
        self.assertEqual(self.g.Events.GameCoreEventPlaybackComplete.Count(), 0)
        self.assertTrue(self.lua.eval('UnitManager==TestOriginalFlagManager'))
        self.assertTrue(self.w.nativeShutdown)

    def test_flag_missing_move_enum_does_not_intercept_nil_operation(self):
        request = self.flag_context()
        self.g.UnitOperationTypes.MOVE_TO = None
        self.assertEqual(request(self.unit, None, self.lua.table_from({'x': 3, 'y': 2})),
                         ('native', None, 19))
        self.assertIsNone(self.w.opened)


if __name__ == '__main__':
    unittest.main()
