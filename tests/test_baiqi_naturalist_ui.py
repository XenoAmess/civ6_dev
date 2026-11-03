import unittest
from lupa.lua53 import LuaRuntime
from naturalist_ui_harness import ROOT, install_naturalist_bridge

KEY = 'BAIQI_NATURALIST_INTENTS_V1'


class NaturalistUITests(unittest.TestCase):
    def setUp(self):
        self.lua = LuaRuntime(unpack_returned_tuples=True)
        for name in ('mock_world', 'mock_missionary', 'mock_naturalist'):
            self.lua.execute((ROOT / f'tests/lua/{name}.lua').read_text(encoding='utf-8'))
        self.logs = []
        self.lua.globals().print = lambda *args: self.logs.append(' '.join(map(str, args)))
        install_naturalist_bridge(self.lua)
        for name in ('BaiqiConfig', 'BaiqiPolicy', 'BaiqiPlanner', 'BaiqiHeritageCandidates', 'BaiqiHeritageActions', 'BaiqiController'):
            self.lua.execute((ROOT / f'mod/Baiqi/Lua/{name}.lua').read_text(encoding='utf-8'))
        self.w, self.h, self.c = self.lua.globals().TestWorld, self.lua.globals().TestParkBridge, self.lua.globals().BaiqiController

    def tearDown(self):
        self.assertFalse(any('|error|' in line for line in self.logs), self.logs)

    def entry(self):
        return self.h.store[KEY].operations['4']

    def reload(self):
        self.c.Shutdown()
        saved = self.h.Copy(self.h.store)
        install_naturalist_bridge(self.lua, saved)
        self.h = self.lua.globals().TestParkBridge
        self.lua.execute((ROOT / 'mod/Baiqi/Lua/BaiqiController.lua').read_text(encoding='utf-8'))
        self.c = self.lua.globals().BaiqiController

    def test_core_permission_precedes_sole_native_park_call(self):
        self.lua.execute('''
          TestWorld.onPark=function(unit,operation,parameters)
            local op=TestParkBridge.store.BAIQI_NATURALIST_INTENTS_V1.operations['4']
            assert(op.stage=='ARMED' and op.charges==1 and op.x==2 and op.y==3)
            assert(parameters==nil and operation==1031611255)
            local coreUnit=TestParkBridge.core.Players[7]:GetUnits():FindID(4)
            assert(coreUnit.GetUnitType==nil and coreUnit:GetParkCharges()==1)
          end
        ''')
        self.c.RunNow()
        self.assertEqual(len(self.w.parkRequests), 1, self.logs)
        self.assertEqual(self.entry().token, 'park:7:1')
        self.assertEqual(len(self.w.unitRequests), 0)

    def test_actual_park_fact_confirms_even_consumed_unit(self):
        self.w.autoPark = True
        self.c.RunNow()
        self.c.RunNow()
        self.assertEqual((len(self.w.parkRequests), self.entry().stage), (1, 'OBSERVED'), self.logs)
        self.assertFalse(self.w.withMissionary)

    def test_unknown_survives_reload_and_missing_unit_without_replay(self):
        self.c.RunNow()
        self.w.withMissionary = False
        self.reload()
        for _ in range(3):
            self.w.turn += 1
            self.c.Update(3)
        self.assertEqual((len(self.w.parkRequests), self.entry().stage), (1, 'ARMED'), self.logs)

    def test_changed_proposal_after_native_qualification_is_not_dispatched(self):
        self.lua.execute('TestWorld.onParkQualification=function() TestWorld.parkCandidates={} end')
        self.c.RunNow()
        self.assertEqual(len(self.w.parkRequests), 0, self.logs)
        self.assertIsNone(self.entry())

    def test_post_grant_change_holds_permission_and_never_replays(self):
        self.lua.execute('''
          local bridge=ExposedMembers.BaiqiNaturalistIntentBridge
          local prepare=bridge.Prepare
          bridge.Prepare=function(...)
            local granted,token,reason=prepare(...)
            assert(granted);TestWorld.missionaryFormation=2
            return granted,token,reason
          end
        ''')
        self.c.RunNow()
        self.assertEqual((len(self.w.parkRequests), self.entry().stage), (0, 'ARMED'))
        self.w.missionaryFormation = 1
        self.reload()
        self.w.turn += 1
        self.c.RunNow()
        self.assertEqual((len(self.w.parkRequests), self.entry().stage), (0, 'ARMED'))

    def test_one_candidate_path_per_callback_then_next_candidate(self):
        self.w.parkCandidates = self.lua.table_from([44, 43])
        self.w.noPathIndex = 43
        self.c.RunNow()
        self.assertEqual(list(self.w.pathTargets.values()), [43], self.logs)
        self.assertEqual(len(self.w.unitRequests), 0)
        self.c.RunNow()
        self.assertEqual(list(self.w.pathTargets.values()), [43, 44], self.logs)
        self.assertEqual((len(self.w.unitRequests), self.w.unitRequests[1].params[14]), (1, 3))

    def test_native_qualification_lost_after_grant_is_held_without_replay(self):
        self.lua.execute('''
          local bridge=ExposedMembers.BaiqiNaturalistIntentBridge
          local prepare=bridge.Prepare
          bridge.Prepare=function(...)
            local granted,token,reason=prepare(...)
            assert(granted);TestWorld.parkLegal=false
            return granted,token,reason
          end
        ''')
        self.c.RunNow()
        self.assertEqual((len(self.w.parkRequests), self.entry().stage), (0, 'ARMED'))
        self.w.parkLegal = True
        self.reload()
        self.w.turn += 1
        self.c.RunNow()
        self.assertEqual((len(self.w.parkRequests), self.entry().stage), (0, 'ARMED'))

    def test_formation_hidden_or_foreign_targets_have_no_paths_or_parks(self):
        for field, value in (('missionaryFormation', 2), ('visible', False), ('plotOwner', 8)):
            with self.subTest(field=field):
                self.setUp()
                self.w[field] = value
                self.c.RunNow()
                self.assertEqual((len(self.w.pathTargets), len(self.w.parkRequests)), (0, 0), self.logs)

    def test_permission_failure_does_not_stop_city_production(self):
        self.h.allowWrite = False
        self.c.RunNow()
        self.w.queueSize = 0
        self.c.RefreshProduction()
        self.c.RunNow()
        self.assertEqual((len(self.w.parkRequests), len(self.w.cityRequests)), (0, 1), self.logs)

    def test_human_guard_blocks_naturalist_and_formation_but_preserves_manual_units(self):
        lua = LuaRuntime(unpack_returned_tuples=True)
        for path in ('tests/lua/mock_guard.lua', 'mod/Baiqi/Lua/BaiqiConfig.lua', 'mod/Baiqi/Lua/BaiqiPolicy.lua'):
            lua.execute((ROOT / path).read_text(encoding='utf-8'))
        lua.execute("GameInfo.Units[17]={UnitType='UNIT_NATURALIST'}")
        lua.execute((ROOT / 'mod/Baiqi/Lua/BaiqiUIGuard.lua').read_text(encoding='utf-8'))
        lua.execute('''
          local naturalist=TestUnit(17,7,100)
          for _,key in ipairs({'RequestOperation','RequestCommand','CanStartOperation','CanStartCommand'}) do
            assert(UnitManager[key](naturalist,1031611255)==false)
          end
          local army=TestUnit(0,7,101)
          assert(UnitManager.RequestCommand(army,10,{owner=7,id=100})==false)
          assert(TestGuard.unitCalls==0)
          for _,kind in ipairs({0,14,15,16}) do assert(UnitManager.RequestOperation(TestUnit(kind),99)==true) end
          assert(TestGuard.unitCalls==4)
        ''')


if __name__ == '__main__':
    unittest.main()
