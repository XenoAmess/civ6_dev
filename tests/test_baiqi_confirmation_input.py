"""Modal confirmation followed by the native map double-click input path."""
from pathlib import Path
import unittest

from lupa.lua51 import LuaRuntime as Lua51
from lupa.lua53 import LuaRuntime as Lua53

ROOT = Path(__file__).resolve().parents[1]


class ConfirmationInputTests(unittest.TestCase):
    source_root = ROOT / 'mod/Baiqi'

    def world(self, runtime):
        lua = runtime(unpack_returned_tuples=True)
        lua.execute((ROOT / 'tests/lua/mock_requisition.lua').read_text(encoding='utf-8'))
        lua.execute('''
          TestUI()
          MouseEvents={LButtonDown=1,LButtonUp=2,MouseMove=3,LButtonDoubleClick=4,
            RButtonDown=5,MButtonDown=6,PointerLeave=7}
          KeyEvents={KeyDown=8}
          function TestEvent()
            local handlers={}
            local event={Add=function(fn) handlers[fn]=true end,
              Remove=function(fn) handlers[fn]=nil end,
              Count=function() local n=0;for _ in pairs(handlers) do n=n+1 end;return n end}
            return setmetatable(event,{__call=function(_,...) for fn in pairs(handlers) do fn(...) end end})
          end
          LuaEvents=setmetatable({},{__index=function(t,k) local e=TestEvent();t[k]=e;return e end})
          Events={GameCoreEventPlaybackComplete=TestEvent()}
          ContextPtr={SetInputHandler=function(_,fn,bubble) assert(bubble==true);TestBoundInput=fn end,
            SetShutdown=function(_,fn) TestShutdown=fn end}
          TestCapture.nativeInputs=0;TestCapture.nativeMoves=0;TestCapture.nativeShutdown=0
          function TestInput(message) return {GetMessageType=function() return message end} end
          function LoadNativeInput()
            MoveUnitToPlot=function(unit,x,y)
              TestCapture.nativeMoves=TestCapture.nativeMoves+1
              TestCapture.queued={unit=unit:GetID(),x=x,y=y}
            end
            OnInputHandler=function(input,...)
              TestCapture.nativeInputs=TestCapture.nativeInputs+1
              TestCapture.extraCount=select('#',...);TestCapture.extra={...}
              if TestCapture.nativeError then error(TestCapture.nativeError) end
              -- Stock OnSelectionDoubleTap resolves MoveUnitToPlot via the
              -- selected unit and the cursor; this is the observed empty tile.
              if input:GetMessageType()==MouseEvents.LButtonDoubleClick then
                MoveUnitToPlot(UI.GetHeadSelectedUnit(),4,2)
              end
              return 'native',nil,19
            end
            ContextPtr:SetInputHandler(OnInputHandler,true)
            OnShutdown=function() TestCapture.nativeShutdown=TestCapture.nativeShutdown+1 end
          end
          function OtherActionsContext(source)
            local env=setmetatable({include=function() end},{__index=_G})
            local fn
            if setfenv then fn=assert(loadstring(source));setfenv(fn,env)
            else fn=assert(load(source,'other-actions','t',env)) end
            fn();return env.BaiqiActions
          end
        ''')

        def include(name):
            if name == 'PopupDialog':
                return
            if name == 'BaiqiUIGuard':
                lua.execute('BaiqiUIGuard={Civilian=function() return false end}')
            elif name == 'BaiqiUILoader':
                lua.execute('BaiqiUILoader={Load=function() LoadNativeInput() end,ReadOnly=function() end}')
            else:
                path = self.source_root / f'Lua/{name}.lua'
                if not path.exists():
                    path = ROOT / f'mod/Baiqi/Lua/{name}.lua'
                lua.execute(path.read_text(encoding='utf-8'))

        lua.globals().include = include
        lua.execute((self.source_root / 'UI/BaiqiWorldInput.lua').read_text(encoding='utf-8'))
        return lua, lua.globals(), lua.globals().TestCapture

    def confirm_then_receive_result(self, lua, g, w, actions=None):
        actions = actions or g.BaiqiActions
        self.assertTrue(actions.Interact(g.UI.GetHeadSelectedUnit(), 3, 2, g.MoveUnitToPlot))
        w.confirm()
        self.assertEqual(len(w.requests), 1)
        w.moves = 0
        w.props.BAIQI_REQUISITION_RESULT = lua.table_from(
            {'id': w.requests[1].requestID, 'stage': 'COMMITTED'})
        actions.Poll()  # The guard must survive clearing the temporary pending request.

    def test_confirmation_result_then_second_click_never_queues_army_move(self):
        for vm in (Lua51, Lua53):
            with self.subTest(vm=vm.__module__):
                lua, g, w = self.world(vm)
                self.confirm_then_receive_result(lua, g, w)
                result = g.TestBoundInput(g.TestInput(g.MouseEvents.LButtonDoubleClick))
                self.assertIsNone(w.queued)
                self.assertEqual((w.nativeMoves, w.nativeInputs, len(w.requests)), (0, 0, 1))
                self.assertTrue(result)

    def test_button_up_and_mouse_move_keep_protection_until_double_click(self):
        for vm in (Lua51, Lua53):
            with self.subTest(vm=vm.__module__):
                lua, g, w = self.world(vm)
                self.confirm_then_receive_result(lua, g, w)
                for message in (g.MouseEvents.LButtonUp, g.MouseEvents.MouseMove):
                    self.assertEqual(g.TestBoundInput(g.TestInput(message)), ('native', None, 19))
                self.assertTrue(g.TestBoundInput(g.TestInput(g.MouseEvents.LButtonDoubleClick)))
                self.assertEqual((w.nativeMoves, w.nativeInputs), (0, 2))

    def test_new_button_or_key_input_preserves_a_deliberate_army_command(self):
        for vm in (Lua51, Lua53):
            for message in (1, 5, 6, 7, 8):
                with self.subTest(vm=vm.__module__, message=message):
                    lua, g, w = self.world(vm)
                    self.confirm_then_receive_result(lua, g, w)
                    self.assertEqual(g.TestBoundInput(g.TestInput(message)), ('native', None, 19))
                    self.assertEqual(g.TestBoundInput(g.TestInput(4)), ('native', None, 19))
                    self.assertEqual((w.nativeMoves, w.nativeInputs, w.queued.x, w.queued.y), (1, 2, 4, 2))

    def test_another_ui_context_notifies_the_world_input_guard(self):
        for vm in (Lua51, Lua53):
            with self.subTest(vm=vm.__module__):
                lua, g, w = self.world(vm)
                other = g.OtherActionsContext((self.source_root / 'Lua/BaiqiActions.lua').read_text(encoding='utf-8'))
                self.confirm_then_receive_result(lua, g, w, other)
                self.assertTrue(g.TestBoundInput(g.TestInput(4)))
                self.assertEqual((w.nativeInputs, w.nativeMoves, len(w.requests)), (0, 0, 1))

    def test_stale_turn_or_player_does_not_intercept_future_input(self):
        for vm in (Lua51, Lua53):
            for field, value in (('turn', 9), ('localPlayer', 3), ('leader', 'LEADER_TRAJAN')):
                with self.subTest(vm=vm.__module__, field=field):
                    lua, g, w = self.world(vm)
                    self.confirm_then_receive_result(lua, g, w)
                    w[field] = value
                    self.assertEqual(g.TestBoundInput(g.TestInput(4)), ('native', None, 19))
                    self.assertEqual(w.nativeInputs, 1)

    def test_unarmed_input_keeps_self_nil_arguments_returns_and_error_object(self):
        for vm in (Lua51, Lua53):
            with self.subTest(vm=vm.__module__):
                lua, g, w = self.world(vm)
                self.assertEqual(g.TestBoundInput(g.TestInput(3), 'intent', None, 7), ('native', None, 19))
                self.assertEqual((w.extraCount, w.extra[1], w.extra[2], w.extra[3]), (3, 'intent', None, 7))
                lua.execute('TestCapture.nativeError={};local ok,err=pcall(TestBoundInput,TestInput(3));assert(not ok and err==TestCapture.nativeError)')
                self.assertEqual(w.nativeInputs, 2)

    def test_cancel_and_native_attack_keep_the_original_first_action(self):
        for vm in (Lua51, Lua53):
            for callback in ('cancel', 'normalAttack'):
                with self.subTest(vm=vm.__module__, callback=callback):
                    lua, g, w = self.world(vm)
                    g.BaiqiActions.Interact(g.UI.GetHeadSelectedUnit(), 3, 2, lua.eval('function() TestCapture.nativeMoves=TestCapture.nativeMoves+1 end'))
                    w[callback]()
                    self.assertEqual((len(w.requests), w.nativeMoves), (0, 1 if callback == 'normalAttack' else 0))
                    self.assertEqual(g.TestBoundInput(g.TestInput(3)), ('native', None, 19))

    def test_shutdown_removes_only_its_own_confirmation_listener(self):
        for vm in (Lua51, Lua53):
            with self.subTest(vm=vm.__module__):
                lua, g, w = self.world(vm)
                event = g.LuaEvents.BaiqiCityConfirmationSubmitted
                lua.execute('TestForeignListener=function() end;LuaEvents.BaiqiCityConfirmationSubmitted.Add(TestForeignListener)')
                self.assertEqual(event.Count(), 2)
                g.TestShutdown()
                self.assertEqual((event.Count(), g.Events.GameCoreEventPlaybackComplete.Count(), w.nativeShutdown), (1, 0, 1))


if __name__ == '__main__':
    unittest.main()
