"""Load real wrappers with native UI doubles that capture request callbacks."""
from pathlib import Path
import unittest
from lupa.lua53 import LuaRuntime

ROOT = Path(__file__).resolve().parents[1]


class UIContextTests(unittest.TestCase):
    def load_context(self, name, leader='LEADER_BAIQI'):
        lua = LuaRuntime(unpack_returned_tuples=True)
        lua.execute((ROOT / 'tests/lua/mock_guard.lua').read_text(encoding='utf-8'))
        lua.globals().TestGuard.leader = leader
        lua.execute("GameConfiguration.GetValue=function() return 'RULESET_EXPANSION_2' end; TestNativeIncludes={}")
        def include(module):
            native = {'ResearchChooser_Expansion1': 'OnChooseResearch', 'CivicsChooser': 'OnChooseCivic',
                      'PantheonChooser': 'ConfirmPantheon', 'ReligionScreen': 'TestReligionConfirm',
                      'DedicationPopup': 'OnConfirm'}
            if module in native:
                lua.execute('TestNativeIncludes[#TestNativeIncludes+1]=...' , module)
                # Mirrors the relevant native request boundary, not mod behavior.
                lua.execute('''
                  local request=UI.RequestPlayerOperation
                  local operation=...
                  TestCapturedButton=function(hash) return request(7,operation,{hash=hash}) end
                ''', 31 if module.startswith('Research') else 32)
                lua.globals()[native[module]] = lua.globals().TestCapturedButton
            elif module == 'UnitFlagManager':
                lua.execute('''
                  TestNativeIncludes[#TestNativeIncludes+1]='UnitFlagManager'
                  local request=UnitManager.RequestOperation
                  TestFlagClick=function(unit) return request(unit,99,{}) end
                ''')
            elif module == 'NaturalDisasterPopup':
                lua.execute('''
                  TestNativeIncludes[#TestNativeIncludes+1]='NaturalDisasterPopup'
                  TestDisasterNativeCalls=0
                  ShowRandomEvent=function(a,b) TestDisasterNativeCalls=TestDisasterNativeCalls+1;return a,b end
                  -- Event registration captures this function object; its global
                  -- ShowRandomEvent lookup still resolves at event invocation.
                  local nativeEvent=function(a,b) return ShowRandomEvent(a,b) end
                  TestDisasterStartedEvent=nativeEvent
                  Game.GetCurrentGameTurn=function() return 9 end
                ''')
            else:
                lua.execute((ROOT / f'mod/Baiqi/Lua/{module}.lua').read_text(encoding='utf-8'))
        lua.globals().include = include
        lua.execute((ROOT / f'mod/Baiqi/UI/Baiqi{name}.lua').read_text(encoding='utf-8'))
        return lua

    def test_quick_choosers_block_direct_and_previously_captured_native_callbacks(self):
        for name,callback,native in [('ResearchChooser','OnChooseResearch','ResearchChooser_Expansion1'), ('CivicsChooser','OnChooseCivic','CivicsChooser')]:
            with self.subTest(context=name):
                lua = self.load_context(name)
                g = lua.globals()
                self.assertFalse(g[callback](100))
                self.assertFalse(g.TestCapturedButton(100))
                self.assertEqual(g.TestGuard.playerCalls, 0)
                self.assertEqual((len(g.TestNativeIncludes),g.TestNativeIncludes[1]), (1,native))

    def test_quick_choosers_preserve_other_leader_callbacks(self):
        for name,callback in [('ResearchChooser','OnChooseResearch'), ('CivicsChooser','OnChooseCivic')]:
            with self.subTest(context=name):
                lua = self.load_context(name,'LEADER_TRAJAN')
                g = lua.globals()
                self.assertTrue(g[callback](100))
                self.assertTrue(g.TestCapturedButton(100))
                self.assertEqual(g.TestGuard.playerCalls, 2)

    def test_flag_context_captures_guard_before_native_initialization(self):
        lua = self.load_context('UnitFlagManager')
        g = lua.globals()
        self.assertFalse(g.TestFlagClick(g.TestUnit(1,7,8)))
        self.assertEqual(g.TestGuard.unitCalls, 0)
        self.assertEqual(g.TestFlagClick(g.TestUnit(0,7,9)), (True,'native'))
        g.TestGuard.leader = 'LEADER_TRAJAN'
        self.assertEqual(g.TestFlagClick(g.TestUnit(1,7,8)), (True,'native'))
        self.assertEqual(g.TestGuard.unitCalls, 2)

    def test_religion_contexts_guard_captured_native_requests_without_changing_executor(self):
        for name in ('PantheonChooser', 'ReligionScreen', 'DedicationPopup'):
            for leader in ('LEADER_BAIQI', 'LEADER_TRAJAN'):
                with self.subTest(context=name, leader=leader):
                    lua = self.load_context(name, leader)
                    g = lua.globals()
                    self.assertEqual(g.TestCapturedButton(505), leader == 'LEADER_TRAJAN')
                    self.assertEqual(g.TestGuard.playerCalls, int(leader == 'LEADER_TRAJAN'))
                    self.assertEqual((len(g.TestNativeIncludes), g.TestNativeIncludes[1]), (1, name))
                    if name == 'PantheonChooser':
                        self.assertEqual(g.ConfirmPantheon(505), leader == 'LEADER_TRAJAN')

    def test_disaster_captured_native_event_skips_cinematic_only_for_baiqi(self):
        lua = self.load_context('NaturalDisasterPopup')
        g = lua.globals()
        self.assertIsNone(g.TestDisasterStartedEvent(11, 22))
        self.assertEqual(g.TestDisasterNativeCalls, 0)
        g.TestGuard.leader = 'LEADER_TRAJAN'
        self.assertEqual(g.TestDisasterStartedEvent(11, 22), (11, 22))
        self.assertEqual(g.TestDisasterNativeCalls, 1)


if __name__ == '__main__':
    unittest.main()
