"""Load real wrappers with native UI doubles that capture request callbacks."""
from pathlib import Path
import unittest
from lupa.lua53 import LuaRuntime

ROOT = Path(__file__).resolve().parents[1]


class UIContextTests(unittest.TestCase):
    def load_context(self, name, leader='LEADER_BAIQI', multi=False):
        lua = LuaRuntime(unpack_returned_tuples=True)
        lua.execute((ROOT / 'tests/lua/mock_guard.lua').read_text(encoding='utf-8'))
        lua.globals().TestGuard.leader = leader
        lua.globals().TestGuard.multi = multi
        lua.execute("GameConfiguration.GetValue=function() return 'RULESET_EXPANSION_2' end; TestNativeIncludes={}")
        lua.execute('''
          GameConfiguration.IsHotseat=function() return false end
          Game.GetCurrentGameTurn=function() return 9 end
          TestPopupNativeCalls=0
          function TestEvent()
            local handlers={}
            return {Add=function(fn) handlers[fn]=true end,Remove=function(fn) handlers[fn]=nil end,
              Fire=function(...) for fn in pairs(handlers) do fn(...) end end,
              Count=function() local n=0;for _ in pairs(handlers) do n=n+1 end;return n end}
          end
        ''')
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
            elif module == 'TechCivicCompletedPopup':
                lua.execute('''
                  TestNativeIncludes[#TestNativeIncludes+1]='TechCivicCompletedPopup'
                  AddCompletedPopup=function(...) TestPopupNativeCalls=TestPopupNativeCalls+1;return ... end
                  -- Registration captured the caller, not the AddCompletedPopup value.
                  TestTechDiscovered=function(pid,index,user) return AddCompletedPopup(pid,nil,index,user) end
                  TestCivicDiscovered=function(pid,index,user) return AddCompletedPopup(pid,index,nil,user) end
                ''')
            elif module == 'NotificationPanel':
                lua.execute('''
                  TestNativeIncludes[#TestNativeIncludes+1]='NotificationPanel'
                  NotificationTypes={TECH_BOOST=1,CIVIC_BOOST=2,COMMAND_UNITS=3}
                  g_notificationHandlers={}
                  function RegisterHandlers()
                    for i=1,3 do g_notificationHandlers[i]={Activate=function(...)
                      TestPopupNativeCalls=TestPopupNativeCalls+1;return ... end} end
                  end
                  -- Native initialization defers registration to OnInit.
                  TestNotificationInit=function() RegisterHandlers() end
                  TestActivateNotification=function(kind,...)
                    return g_notificationHandlers[kind].Activate(...)
                  end
                ''')
            elif module == 'NaturalWonderPopup':
                lua.execute('''
                  TestNativeIncludes[#TestNativeIncludes+1]='NaturalWonderPopup'
                  Events={NaturalWonderRevealed=TestEvent()}
                  OnNaturalWonderRevealed=function(...) TestPopupNativeCalls=TestPopupNativeCalls+1 end
                  if not GameConfiguration.IsAnyMultiplayer() and not GameConfiguration.IsHotseat() then
                    Events.NaturalWonderRevealed.Add(OnNaturalWonderRevealed)
                  end
                ''')
            elif module == 'GreatWorkShowcase':
                lua.execute('''
                  TestNativeIncludes[#TestNativeIncludes+1]='GreatWorkShowcase'
                  Events={GreatWorkCreated=TestEvent()}
                  OnGreatWorkCreated=function(...) TestPopupNativeCalls=TestPopupNativeCalls+1 end
                  Events.GreatWorkCreated.Add(OnGreatWorkCreated)
                  OnViewGreatWork=function(...) TestPopupNativeCalls=TestPopupNativeCalls+1 end
                ''')
            elif module == 'HistoricMoments':
                lua.execute('''
                  TestNativeIncludes[#TestNativeIncludes+1]='HistoricMoments'
                  HasCapability=function() return true end
                  DB={MakeHash=function(s) assert(s=='NOTIFICATION_PRIDE_MOMENT_RECORDED');return 88 end}
                  NotificationManager={Find=function(_,id) return {GetType=function() return id end} end}
                  Events={NotificationActivated=TestEvent()}
                  OnProcessNotification=function(...) TestPopupNativeCalls=TestPopupNativeCalls+1 end
                  Events.NotificationActivated.Add(OnProcessNotification)
                  ToggleHistoricMomentsScreen=function() TestPopupNativeCalls=TestPopupNativeCalls+1 end
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

    def test_completion_captured_callers_skip_automatic_but_keep_explicit_inspection(self):
        lua = self.load_context('TechCivicCompletedPopup')
        g = lua.globals()
        g.TestTechDiscovered(7, 4, False)
        g.TestCivicDiscovered(7, 5, None)
        self.assertEqual(g.TestPopupNativeCalls, 0)
        self.assertEqual(g.TestTechDiscovered(7, 4, True), (7, None, 4, True))
        g.TestGuard.leader = 'LEADER_TRAJAN'
        g.TestCivicDiscovered(7, 5, False)
        self.assertEqual(g.TestPopupNativeCalls, 2)

    def test_boost_registration_is_guarded_after_native_init_and_refresh(self):
        lua = self.load_context('NotificationPanel')
        g = lua.globals()
        entry = lua.table_from({'m_PlayerID': 7})
        for _ in range(2):
            g.TestNotificationInit()
            before = g.TestPopupNativeCalls
            g.TestActivateNotification(1, entry, 42, False)
            g.TestActivateNotification(2, entry, 43, None)
            self.assertEqual(g.TestPopupNativeCalls, before)
            g.TestActivateNotification(1, entry, 42, True)
            g.TestActivateNotification(3, entry, 44, False)
            self.assertEqual(g.TestPopupNativeCalls, before+2)
        g.TestGuard.leader = 'LEADER_TRAJAN'
        g.TestActivateNotification(2, entry, 43, False)
        self.assertEqual(g.TestPopupNativeCalls, 5)
        self.assertEqual((len(g.TestNativeIncludes),g.TestNativeIncludes[1]), (1,'NotificationPanel'))

    def test_natural_wonder_captured_callback_is_replaced_once_before_lock(self):
        lua = self.load_context('NaturalWonderPopup')
        g = lua.globals()
        self.assertEqual(g.Events.NaturalWonderRevealed.Count(), 1)
        g.Events.NaturalWonderRevealed.Fire(1, 2, 3, True)
        self.assertEqual(g.TestPopupNativeCalls, 0)
        g.TestGuard.leader = 'LEADER_TRAJAN'
        g.Events.NaturalWonderRevealed.Fire(1, 2, 3, True)
        self.assertEqual(g.TestPopupNativeCalls, 1)

    def test_history_keeps_manual_notification_and_timeline_without_duplicate_handler(self):
        lua = self.load_context('HistoricMoments')
        g = lua.globals()
        self.assertEqual(g.Events.NotificationActivated.Count(), 1)
        g.Events.NotificationActivated.Fire(7, 88, False)
        self.assertEqual(g.TestPopupNativeCalls, 0)
        g.Events.NotificationActivated.Fire(7, 88, True)
        g.ToggleHistoricMomentsScreen()
        g.Events.NotificationActivated.Fire(7, 99, False)
        self.assertEqual(g.TestPopupNativeCalls, 3)
        g.TestGuard.leader = 'LEADER_TRAJAN'
        g.Events.NotificationActivated.Fire(7, 88, False)
        self.assertEqual(g.TestPopupNativeCalls, 4)
        self.assertEqual(g.TestNativeIncludes[1], 'HistoricMoments')

    def test_quiet_wrappers_preserve_multiplayer_native_registration(self):
        lua = self.load_context('NaturalWonderPopup', multi=True)
        g = lua.globals()
        self.assertEqual(g.Events.NaturalWonderRevealed.Count(), 0)
        lua = self.load_context('TechCivicCompletedPopup', multi=True)
        lua.globals().TestTechDiscovered(7, 4, False)
        self.assertEqual(lua.globals().TestPopupNativeCalls, 1)

    def test_creative_native_event_skips_only_automatic_baiqi_showcase_and_keeps_manual_view(self):
        lua = self.load_context('GreatWorkShowcase')
        g = lua.globals()
        self.assertEqual(g.Events.GreatWorkCreated.Count(), 1)
        g.Events.GreatWorkCreated.Fire(7, 999, 2, 3, 4, 5)
        self.assertEqual(g.TestPopupNativeCalls, 0)
        g.OnViewGreatWork(2, 3, 4)
        g.Events.GreatWorkCreated.Fire(8, 999, 2, 3, 4, 5)
        self.assertEqual(g.TestPopupNativeCalls, 2)
        g.TestGuard.leader = 'LEADER_TRAJAN'
        g.Events.GreatWorkCreated.Fire(7, 999, 2, 3, 4, 5)
        self.assertEqual(g.TestPopupNativeCalls, 3)
        lua = self.load_context('GreatWorkShowcase', multi=True)
        lua.globals().Events.GreatWorkCreated.Fire(7, 999, 2, 3, 4, 5)
        self.assertEqual(lua.globals().TestPopupNativeCalls, 1)


if __name__ == '__main__':
    unittest.main()
