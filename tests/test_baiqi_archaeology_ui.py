import unittest
from lupa.lua53 import LuaRuntime
from archaeology_ui_harness import ROOT, KEY, install_archaeology_bridge


class ArchaeologyUITests(unittest.TestCase):
    def setUp(self):
        self.lua = LuaRuntime(unpack_returned_tuples=True)
        for name in ('mock_world', 'mock_missionary', 'mock_archaeology'):
            self.lua.execute((ROOT / f'tests/lua/{name}.lua').read_text(encoding='utf-8'))
        self.logs = []
        self.lua.globals().print = lambda *args: self.logs.append(' '.join(map(str, args)))
        install_archaeology_bridge(self.lua)
        for name in ('BaiqiConfig', 'BaiqiPolicy', 'BaiqiPlanner', 'BaiqiHeritageCandidates', 'BaiqiHeritageActions',
                     'BaiqiArchaeologyHome', 'BaiqiPendingArtifact', 'BaiqiController'):
            self.lua.execute((ROOT / f'mod/Baiqi/Lua/{name}.lua').read_text(encoding='utf-8'))
        self.w, self.h, self.c = self.lua.globals().TestWorld, self.lua.globals().TestArchBridge, self.lua.globals().BaiqiController

    def tearDown(self):
        self.assertFalse(any('|error|' in line for line in self.logs), self.logs)

    def entry(self):
        journal = self.h.store[KEY]
        return journal and journal.operations['4']

    def reload(self):
        self.c.Shutdown()
        saved = self.h.Copy(self.h.store)
        install_archaeology_bridge(self.lua, saved)
        self.h = self.lua.globals().TestArchBridge
        self.lua.execute((ROOT / 'mod/Baiqi/Lua/BaiqiController.lua').read_text(encoding='utf-8'))
        self.c = self.lua.globals().BaiqiController

    def test_both_core_phases_precede_sole_native_calls_and_zero_moves_choice(self):
        self.w.autoExcavate = True
        self.lua.execute('''
          TestWorld.onExcavate=function(unit,operation)
            local op=TestArchBridge.store.BAIQI_ARCHAEOLOGY_INTENTS_V1.operations['4']
            assert(op.stage=='EXCAVATE_ARMED' and op.token=='archaeology:7:1')
            assert(operation==1548958412 and unit:GetID()==4)
            local core=TestArchBridge.core.Players[7]:GetUnits():FindID(4)
            assert(core.GetArchaeologyHomeCity==nil and core.GetArchaeology==nil)
          end
          TestWorld.onChoice=function(pid,operation,params)
            local op=TestArchBridge.store.BAIQI_ARCHAEOLOGY_INTENTS_V1.operations['4']
            assert(op.stage=='CHOICE_ARMED' and op.token=='archaeology:7:1')
            assert(pid==7 and operation==-190000001 and params[-190000002]==2)
            assert(TestWorld.missionaryMoves==0)
          end
        ''')
        self.c.RunNow()
        self.assertEqual((len(self.w.archRequests), self.entry().stage), (1, 'EXCAVATE_ARMED'), self.logs)
        self.c.RunNow()
        self.assertEqual((len(self.w.choiceRequests), self.entry().stage), (1, 'CHOICE_ARMED'), self.logs)

    def test_actual_consumer_synthetic_created_event_settles_consumed_unit(self):
        self.w.autoExcavate = self.w.autoChoice = self.w.consumeArch = True
        for _ in range(3):
            self.c.RunNow()
        self.assertEqual((len(self.w.archRequests), len(self.w.choiceRequests), self.entry().stage), (1, 1, 'OBSERVED'), self.logs)
        self.assertEqual((self.entry().newWorkID, self.w.archSlots[1]), (101, 101))
        self.assertTrue(any('proof=core_created_work_receipt' in line for line in self.logs))

    def test_cold_ui_can_complete_real_pending_queue_but_does_not_replay_choice(self):
        self.w.autoExcavate = True
        self.c.RunNow()
        self.reload()
        self.c.RunNow()
        self.assertEqual((len(self.w.choiceRequests), self.entry().stage), (1, 'CHOICE_ARMED'), self.logs)
        self.reload()
        self.w.turn += 1
        for _ in range(3):
            self.c.Update(3)
        self.assertEqual((len(self.w.archRequests), len(self.w.choiceRequests)), (1, 1), self.logs)

    def test_unknown_excavation_survives_cold_ui_without_replay(self):
        self.w.throwExcavate = True
        self.c.RunNow()
        self.assertEqual(self.entry().stage, 'EXCAVATE_ARMED')
        self.reload()
        self.w.turn += 1
        self.c.RunNow()
        self.assertEqual((len(self.w.archRequests), len(self.w.choiceRequests)), (1, 0), self.logs)

    def test_fresh_changes_after_each_native_qualification_block_excavation(self):
        for count in (1, 2):
            with self.subTest(count=count):
                self.setUp()
                self.lua.execute('TestWorld.onArchQualification=function(n) if n==' + str(count) + ' then TestWorld.visible=false end end')
                self.c.RunNow()
                self.assertEqual(len(self.w.archRequests), 0, self.logs)
                self.assertEqual(self.entry() is not None, count == 2)

    def test_exact_resource_action_turn_and_home_changes_after_grant_hold(self):
        for mutation in ('TestWorld.archResource=10', 'GameInfo.UnitOperations.UNITOPERATION_EXCAVATE.Hash=11',
                         'TestWorld.turn=2', 'TestWorld.archSlots[1]=101', 'TestWorld.missionaryFormation=2'):
            with self.subTest(mutation=mutation):
                self.setUp()
                self.lua.execute('''local b=ExposedMembers.BaiqiArchaeologyBridge;local prepare=b.PrepareExcavation
                  b.PrepareExcavation=function(...) local a,t,r=prepare(...);assert(a);''' + mutation + ''';return a,t,r end''')
                self.c.RunNow()
                self.assertEqual((len(self.w.archRequests), self.entry().stage), (0, 'EXCAVATE_ARMED'), self.logs)

    def test_choice_postgrant_queue_metadata_and_home_changes_hold_without_replay(self):
        for mutation in ('TestWorld.artifactIndex=6', 'TestWorld.archSlots[1]=101',
                         'PlayerOperations.PARAM_PLAYER_ONE=17', 'TestWorld.missionaryFormation=2'):
            with self.subTest(mutation=mutation):
                self.setUp()
                self.w.autoExcavate = True
                self.c.RunNow()
                self.lua.execute('''local b=ExposedMembers.BaiqiArchaeologyBridge;local prepare=b.PrepareChoice
                  b.PrepareChoice=function(...) local a,t,r=prepare(...);assert(a);''' + mutation + ''';return a,t,r end''')
                self.c.RunNow()
                self.assertEqual((len(self.w.choiceRequests), self.entry().stage), (0, 'CHOICE_ARMED'), self.logs)
                self.reload()
                self.w.turn += 1
                self.c.RunNow()
                self.assertEqual(len(self.w.choiceRequests), 0)

    def test_absent_home_full_museum_unknown_queue_or_no_permission_does_not_stop_cities(self):
        for mutation in ('TestWorld.archHome=-1', 'TestWorld.archSlots={101,102,103}',
                         'TestWorld.objects.player.GetUnits=function() return {Members=function() return function() end end,FindID=function() end} end',
                         'TestArchBridge.allowWrite=false'):
            with self.subTest(mutation=mutation):
                self.setUp()
                self.lua.execute(mutation)
                self.c.RunNow()
                self.w.queueSize = 0
                self.c.RefreshProduction()
                self.c.RunNow()
                self.assertEqual((len(self.w.archRequests), len(self.w.cityRequests)), (0, 1), self.logs)

    def test_owned_human_guard_blocks_archaeology_and_choice_preserves_other_leader(self):
        lua = LuaRuntime(unpack_returned_tuples=True)
        for path in ('tests/lua/mock_guard.lua', 'mod/Baiqi/Lua/BaiqiConfig.lua', 'mod/Baiqi/Lua/BaiqiPolicy.lua'):
            lua.execute((ROOT / path).read_text(encoding='utf-8'))
        lua.execute("GameInfo.Units[18]={UnitType='UNIT_ARCHAEOLOGIST'};PlayerOperations.CHOOSE_ARTIFACT_PLAYER=-190000001")
        lua.execute((ROOT / 'mod/Baiqi/Lua/BaiqiUIGuard.lua').read_text(encoding='utf-8'))
        lua.execute('''
          local arc=TestUnit(18,7,100)
          for _,name in ipairs({'CanStartOperation','CanStartCommand','RequestOperation','RequestCommand'}) do
            assert(UnitManager[name](arc,1548958412)==false)
          end
          assert(UI.RequestPlayerOperation(7,-190000001,{[-190000002]=2})==false)
          assert(TestGuard.unitCalls==0)
          TestGuard.leader='LEADER_OTHER'
          assert(UnitManager.RequestOperation(arc,1548958412)==true)
          assert(UI.RequestPlayerOperation(7,-190000001,{[-190000002]=2})==true)
          assert(TestGuard.unitCalls==1 and TestGuard.playerCalls==1)
        ''')

    def test_popup_owns_only_native_open_and_guard_precedes_captured_callbacks(self):
        lua = LuaRuntime(unpack_returned_tuples=True)
        for path in ('tests/lua/mock_guard.lua', 'mod/Baiqi/Lua/BaiqiConfig.lua', 'mod/Baiqi/Lua/BaiqiPolicy.lua'):
            lua.execute((ROOT / path).read_text(encoding='utf-8'))
        lua.execute('''
          Popup={listeners={},includes={},opens=0,foreignCalls=0}
          Popup.foreign=function() Popup.foreignCalls=Popup.foreignCalls+1 end
          Popup.listeners[Popup.foreign]=true
          LuaEvents={NotificationPanel_OpenArtifactPanel={
            Add=function(fn) Popup.listeners[fn]=true end,Remove=function(fn) Popup.listeners[fn]=nil end}}
          Controls={Button1={SetDisabled=function(_,value) Popup.disabled1=value end},
            Button2={SetDisabled=function(_,value) Popup.disabled2=value end}}
          BaiqiUILoader={Load=function(name)
            assert(name=='ChooseArtifact')
            local captured=UI.RequestPlayerOperation
            Popup.button1=function() return captured(7,71,{[72]=2}) end
            OnOpen=function() Popup.opens=Popup.opens+1 end
            Popup.native=OnOpen;LuaEvents.NotificationPanel_OpenArtifactPanel.Add(OnOpen)
          end}
          Popup.Emit=function() for callback in pairs(Popup.listeners) do callback() end end
        ''')
        guard = (ROOT / 'mod/Baiqi/Lua/BaiqiUIGuard.lua').read_text(encoding='utf-8')
        def include(name):
            lua.globals().Popup.includes[len(lua.globals().Popup.includes) + 1] = name
            if name == 'BaiqiUIGuard':
                lua.execute(guard)
            elif name in ('BaiqiConfig', 'BaiqiPolicy'):
                lua.execute((ROOT / f'mod/Baiqi/Lua/{name}.lua').read_text(encoding='utf-8'))
            else:
                self.assertEqual(name, 'BaiqiUILoader')
        lua.globals().include = include
        lua.execute((ROOT / 'mod/Baiqi/UI/BaiqiChooseArtifact.lua').read_text(encoding='utf-8'))
        lua.execute('''
          assert(Popup.listeners[Popup.native]==nil and Popup.listeners[Popup.foreign]==true)
          assert(Popup.includes[1]=='BaiqiUIGuard' and Popup.includes[#Popup.includes]=='BaiqiUILoader')
          Popup.Emit()
          assert(Popup.opens==1 and Popup.foreignCalls==1 and Popup.disabled1 and Popup.disabled2)
          assert(Popup.button1()==false and TestGuard.playerCalls==0)
          TestGuard.leader='LEADER_OTHER';Popup.Emit()
          assert(Popup.opens==2 and Popup.disabled1==false and Popup.disabled2==false)
          assert(Popup.button1()==true and TestGuard.playerCalls==1)
        ''')


if __name__ == '__main__':
    unittest.main()
