"""Load real wrappers with native UI doubles that capture request callbacks."""
from pathlib import Path
import unittest
from lupa.lua53 import LuaRuntime

ROOT = Path(__file__).resolve().parents[1]


class UIContextTests(unittest.TestCase):
    def load_context(self, name, leader='LEADER_BAIQI', multi=False, missing_government=False):
        lua = LuaRuntime(unpack_returned_tuples=True)
        lua.execute((ROOT / 'tests/lua/mock_guard.lua').read_text(encoding='utf-8'))
        lua.globals().TestGuard.leader = leader
        lua.globals().TestGuard.multi = multi
        lua.globals().TestMissingGovernmentKind = missing_government
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
            elif module in ('CityStates', 'CityStates_Expansion1', 'CityStates_Expansion2'):
                lua.execute('TestNativeIncludes[#TestNativeIncludes+1]=...', module)
                lua.execute('''
                  PlayerOperations.GIVE_INFLUENCE_TOKEN=35
                  PlayerOperations.PARAM_PLAYER_ONE='target'
                  TestNativeReadOnly=false
                  IsReadOnly=function() return TestNativeReadOnly end
                  local request=UI.RequestPlayerOperation
                  TestCityStateEnvoy=function(target)
                    local params={}
                    params[PlayerOperations.PARAM_PLAYER_ONE]=target
                    return request(7,PlayerOperations.GIVE_INFLUENCE_TOKEN,params)
                  end
                  TestCityStatePeace=function(params)
                    return request(7,PlayerOperations.DIPLOMACY_MAKE_PEACE,params)
                  end
                  TestCityStateLevy=function(params)
                    return request(7,PlayerOperations.LEVY_MILITARY,params)
                  end
                  UI.RequestPlayerOperation=function() error('callback should keep captured native sink') end
                ''')
            elif module in ('GovernmentScreen', 'GovernmentScreen_Expansion1', 'GovernmentScreen_Expansion2'):
                lua.execute('TestNativeIncludes[#TestNativeIncludes+1]=...', module)
                lua.execute('''
                  TestGovernment={visible=true,confirmVisible=true,enabled=true,closed=0,warnings=0,flagWrites=0}
                  Controls={ConfirmPolicies={
                    IsVisible=function() return TestGovernment.confirmVisible end,
                    IsEnabled=function() return TestGovernment.enabled end,
                    SetDisabled=function(_,value)
                      TestGovernment.flagWrites=TestGovernment.flagWrites+1
                      TestGovernment.enabled=not value
                    end}}
                  IsReadOnly=function() return false end
                  function Close(...)
                    if Controls.ConfirmPolicies and Controls.ConfirmPolicies:IsVisible()
                      and Controls.ConfirmPolicies:IsEnabled() then
                      TestGovernment.warnings=TestGovernment.warnings+1
                    else TestGovernment.visible=false;TestGovernment.closed=TestGovernment.closed+1 end
                    return 'native_close',...
                  end
                  TestGovernmentCapturedClose=function(...) return Close(...) end
                ''')
            elif module == 'UnitFlagManager':
                lua.execute('''
                  TestNativeIncludes[#TestNativeIncludes+1]='UnitFlagManager'
                  local request=UnitManager.RequestOperation
                  TestFlagClick=function(unit) return request(unit,99,{}) end
                  Events={GameCoreEventPlaybackComplete=TestEvent()}
                  ContextPtr={SetShutdown=function(_,fn) TestFlagShutdown=fn end}
                ''')
            elif module == 'PopupDialog':
                pass
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
                  NotificationTypes={TECH_BOOST=1,CIVIC_BOOST=2,COMMAND_UNITS=3,CONSIDER_GOVERNMENT_CHANGE=4,DIPLOMACY=5}
                  if TestMissingGovernmentKind then NotificationTypes.CONSIDER_GOVERNMENT_CHANGE=nil end
                  LuaEvents={ActionPanel_ActivateNotification=TestEvent()}
                  TestNativeLuaNotificationCalls=0
                  g_notificationHandlers={}
                  function RegisterHandlers()
                    for i=1,5 do g_notificationHandlers[i]={Activate=function(...)
                      TestPopupNativeCalls=TestPopupNativeCalls+1;return ... end} end
                  end
                  -- Same native producer/consumer boundary: ActionPanel routes
                  -- every notification as activatedByUser=true; direct engine
                  -- activation can still carry its original false/true flag.
                  function OnLuaActivateNotification(notification,...)
                    TestNativeLuaNotificationCalls=TestNativeLuaNotificationCalls+1
                    if notification and notification:IsValidForPhase() then
                      local kind,pid=notification:GetType(),notification:GetPlayerID()
                      return g_notificationHandlers[kind].Activate({m_PlayerID=pid},notification:GetID(),true,...)
                    end
                  end
                  -- Native initialization defers registration to OnInit.
                  TestNotificationInit=function()
                    RegisterHandlers()
                    LuaEvents.ActionPanel_ActivateNotification.Add(OnLuaActivateNotification)
                  end
                  TestNotificationShutdown=function()
                    LuaEvents.ActionPanel_ActivateNotification.Remove(OnLuaActivateNotification)
                  end
                  TestNotification=function(kind,pid,id,valid)
                    return {GetType=function() return kind end,GetPlayerID=function() return pid end,
                      GetID=function() return id end,IsValidForPhase=function() return valid~=false end}
                  end
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

    def test_city_state_diplomacy_callbacks_remain_native_for_baiqi(self):
        lua = self.load_context('CityStates')
        g = lua.globals()
        self.assertEqual((len(g.TestNativeIncludes), g.TestNativeIncludes[1]),
                         (1, 'CityStates_Expansion2'))
        self.assertIsNone(g.BaiqiUIGuard)
        self.assertTrue(g.TestCityStateEnvoy(2))
        self.assertEqual((g.TestGuard.lastPlayer, g.TestGuard.lastOperation,
                          g.TestGuard.lastParams.target), (7, 35, 2))
        self.assertTrue(g.TestCityStatePeace(lua.table_from({'target': 2})))
        self.assertTrue(g.TestCityStateLevy(lua.table_from({'target': 2})))
        self.assertEqual(g.TestGuard.playerCalls, 3)
        self.assertFalse(g.IsReadOnly())
        g.TestNativeReadOnly = True
        self.assertTrue(g.IsReadOnly())
        # Context isolation: the existing chooser still blocks its domestic sink.
        other = self.load_context('ResearchChooser')
        self.assertFalse(other.globals().TestCapturedButton(100))
        self.assertEqual(other.globals().TestGuard.playerCalls, 0)

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

    def test_government_turn_blocker_captured_event_does_not_open_choice_viewer(self):
        lua = self.load_context('NotificationPanel')
        g = lua.globals()
        g.TestNotificationInit()
        g.LuaEvents.ActionPanel_ActivateNotification.Fire(g.TestNotification(4, 7, 44, True))
        self.assertEqual((g.TestNativeLuaNotificationCalls, g.TestPopupNativeCalls), (0, 0))
        entry = lua.table_from({'m_PlayerID': 7})
        result = g.TestActivateNotification(4, entry, 44, True, 'inspect', None, 8)
        self.assertTrue(lua.eval('function(a,b) return a==b end')(result[0], entry))
        self.assertEqual(result[1:], (44, True, 'inspect', None, 8))
        self.assertEqual(g.TestPopupNativeCalls, 1)

    def test_government_engine_auto_activation_waits_for_ai_but_manual_inspection_remains(self):
        lua = self.load_context('NotificationPanel')
        g = lua.globals()
        g.TestNotificationInit()
        entry = lua.table_from({'m_PlayerID': 7})
        g.TestActivateNotification(4, entry, 44, False)
        g.TestActivateNotification(4, entry, 44, None)
        self.assertEqual(g.TestPopupNativeCalls, 0)
        g.TestActivateNotification(4, entry, 44, True)
        self.assertEqual(g.TestPopupNativeCalls, 1)

    def test_government_turn_filter_preserves_other_notifications_and_foreign_player(self):
        lua = self.load_context('NotificationPanel')
        g = lua.globals()
        g.TestNotificationInit()
        for kind in (1, 2, 3, 5):
            g.LuaEvents.ActionPanel_ActivateNotification.Fire(g.TestNotification(kind, 7, 100+kind, True))
        g.LuaEvents.ActionPanel_ActivateNotification.Fire(g.TestNotification(4, 8, 44, True))
        self.assertEqual((g.TestNativeLuaNotificationCalls, g.TestPopupNativeCalls), (5, 5))
        self.assertEqual(g.TestGuard.playerCalls, 0)

    def test_government_turn_filter_preserves_other_leader_and_multiplayer(self):
        for kwargs in ({'leader': 'LEADER_TRAJAN'}, {'multi': True}):
            with self.subTest(kwargs=kwargs):
                lua = self.load_context('NotificationPanel', **kwargs)
                g = lua.globals()
                g.TestNotificationInit()
                g.LuaEvents.ActionPanel_ActivateNotification.Fire(g.TestNotification(4, 7, 44, True))
                g.TestActivateNotification(4, lua.table_from({'m_PlayerID': 7}), 44, False)
                self.assertEqual((g.TestNativeLuaNotificationCalls, g.TestPopupNativeCalls), (1, 2))

    def test_government_filter_refresh_shutdown_and_missing_constant_keep_native_shape(self):
        lua = self.load_context('NotificationPanel')
        g = lua.globals()
        for _ in range(2):
            g.TestNotificationInit()
            self.assertEqual(g.LuaEvents.ActionPanel_ActivateNotification.Count(), 1)
            g.LuaEvents.ActionPanel_ActivateNotification.Fire(g.TestNotification(4, 7, 44, True))
        self.assertEqual(g.TestPopupNativeCalls, 0)
        g.TestNotificationShutdown()
        self.assertEqual(g.LuaEvents.ActionPanel_ActivateNotification.Count(), 0)
        lua = self.load_context('NotificationPanel', missing_government=True)
        g = lua.globals()
        g.TestNotificationInit()
        g.LuaEvents.ActionPanel_ActivateNotification.Fire(g.TestNotification(4, 7, 44, True))
        self.assertEqual((g.TestNativeLuaNotificationCalls, g.TestPopupNativeCalls), (1, 1))

    def test_natural_wonder_captured_callback_is_replaced_once_before_lock(self):
        lua = self.load_context('NaturalWonderPopup')
        g = lua.globals()
        self.assertEqual(g.Events.NaturalWonderRevealed.Count(), 1)
        g.Events.NaturalWonderRevealed.Fire(1, 2, 3, True)
        self.assertEqual(g.TestPopupNativeCalls, 0)
        g.TestGuard.leader = 'LEADER_TRAJAN'
        g.Events.NaturalWonderRevealed.Fire(1, 2, 3, True)
        self.assertEqual(g.TestPopupNativeCalls, 1)

    def test_readonly_government_captured_close_discards_ui_state_without_policy_write(self):
        lua = self.load_context('GovernmentScreen')
        g = lua.globals()
        self.assertTrue(g.IsReadOnly())
        self.assertEqual(g.TestGovernmentCapturedClose('button', None, 7), ('native_close', 'button', None, 7))
        self.assertEqual((g.TestGovernment.closed, g.TestGovernment.warnings, g.TestGovernment.flagWrites), (1, 0, 1))
        self.assertFalse(g.TestGovernment.visible)
        self.assertEqual(g.TestGuard.playerCalls, 0)
        self.assertEqual(g.TestNativeIncludes[1], 'GovernmentScreen_Expansion2')

    def test_readonly_government_close_rechecks_after_ai_refresh_reenables_confirm(self):
        lua = self.load_context('GovernmentScreen')
        g = lua.globals()
        for _ in range(2):
            g.TestGovernment.visible, g.TestGovernment.enabled = True, True
            g.TestGovernmentCapturedClose()
        self.assertEqual((g.TestGovernment.closed, g.TestGovernment.warnings, g.TestGovernment.flagWrites), (2, 0, 2))
        self.assertEqual(g.TestGuard.playerCalls, 0)

    def test_government_close_other_leader_and_multiplayer_keep_native_warning(self):
        for kwargs in ({'leader': 'LEADER_TRAJAN'}, {'multi': True}):
            with self.subTest(kwargs=kwargs):
                lua = self.load_context('GovernmentScreen', **kwargs)
                g = lua.globals()
                g.TestGovernmentCapturedClose()
                self.assertEqual((g.TestGovernment.closed, g.TestGovernment.warnings, g.TestGovernment.flagWrites), (0, 1, 0))

    def test_readonly_government_close_tolerates_missing_optional_confirm_control(self):
        lua = self.load_context('GovernmentScreen')
        g = lua.globals()
        g.Controls.ConfirmPolicies = None
        self.assertEqual(g.TestGovernmentCapturedClose('escape'), ('native_close', 'escape'))
        self.assertEqual((g.TestGovernment.closed, g.TestGovernment.warnings, g.TestGovernment.flagWrites), (1, 0, 0))

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
