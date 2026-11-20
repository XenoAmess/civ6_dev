"""Verify guarded human request sinks against unmodified native counters."""
from pathlib import Path
import unittest
from lupa.lua53 import LuaRuntime

ROOT = Path(__file__).resolve().parents[1]


class UIGuardTests(unittest.TestCase):
    def setUp(self):
        self.lua = LuaRuntime(unpack_returned_tuples=True)
        self.lua.execute((ROOT / 'tests/lua/mock_guard.lua').read_text(encoding='utf-8'))
        self.lua.execute('rawset=nil')  # The actual Civ6 UI sandbox omits rawset.
        for name in ('BaiqiConfig', 'BaiqiPolicy', 'BaiqiUIGuard'):
            self.lua.execute((ROOT / f'mod/Baiqi/Lua/{name}.lua').read_text(encoding='utf-8'))
        self.g, self.w = self.lua.globals(), self.lua.globals().TestGuard

    def test_builder_settler_trader_all_manual_command_sinks_and_hotkey_capability_blocked(self):
        for kind in (1, 2, 3, 4, 7, 8, 9, 10, 11, 12, 13, 17, 18):
            unit = self.g.TestUnit(kind, 7, kind)
            for name in ('RequestOperation', 'RequestCommand', 'CanStartOperation', 'CanStartCommand'):
                self.assertFalse(self.g.UnitManager[name](unit, 99, self.lua.table()))
        self.assertEqual(self.w.unitCalls, 0)

    def test_army_native_identity_arguments_and_multi_return_are_preserved(self):
        army = self.g.TestUnit(0, 7, 9)
        self.assertEqual(self.g.UnitManager.RequestOperation(army, 55, self.lua.table()), (True, 'native'))
        self.assertEqual(self.w.lastUnit.GetID(), 9)
        self.assertEqual((self.w.unitCalls, self.w.lastAction), (1, 55))

    def test_military_great_people_keep_native_commands(self):
        for kind in (5, 6):
            unit = self.g.TestUnit(kind, 7, kind)
            self.assertEqual(self.g.UnitManager.RequestCommand(unit, 55), (True, 'native'))
        self.assertEqual(self.w.unitCalls, 2)

    def test_religious_combat_units_keep_player_native_operations_and_commands(self):
        for kind in (14, 15, 16):
            unit = self.g.TestUnit(kind, 7, kind)
            for name in ('RequestOperation', 'RequestCommand', 'CanStartOperation', 'CanStartCommand'):
                self.assertEqual(self.g.UnitManager[name](unit, 55, self.lua.table()), (True, 'native'))
        self.assertEqual(self.w.unitCalls, 12)

    def test_army_can_join_escort_of_delegated_civilian(self):
        army = self.g.TestUnit(0, 7, 9)
        for kind, target_id in ((1, 101), (2, 102), (13, 103)):
            self.g.TestUnit(kind, 7, target_id)
            params = self.lua.table_from({'owner': 7, 'id': target_id})
            self.assertEqual(self.g.UnitManager.CanStartCommand(army, 10, params), (True, 'native'))
            self.assertEqual(self.g.UnitManager.RequestCommand(army, 10, params), (True, 'native'))
            self.assertTrue(self.lua.eval('function(a,b) return a==b end')(self.w.lastUnit, army))
            self.assertTrue(self.lua.eval('function(a,b) return a==b end')(self.w.lastParams, params))
        self.assertEqual(self.w.unitCalls, 6)

    def test_military_formation_target_validation_stays_native(self):
        army = self.g.TestUnit(0, 7, 9)
        other = self.g.TestUnit(0, 7, 8)
        other.GetID = lambda *args: 65544
        params = self.lua.table_from({'owner': 7, 'id': 8})
        self.lua.execute("""
          TestGuard.nativeUnit.CanStartCommand=function(unit,command,params)
            TestGuard.unitCalls=TestGuard.unitCalls+1
            return false,'native_target_invalid'
          end
          TestGuard.nativeUnit.RequestCommand=TestGuard.nativeUnit.CanStartCommand
        """)
        self.assertEqual(self.g.UnitManager.CanStartCommand(army, 10, params), (False, 'native_target_invalid'))
        self.assertEqual(self.g.UnitManager.RequestCommand(army, 10, params), (False, 'native_target_invalid'))
        self.assertEqual(self.w.unitCalls, 2)

    def test_civilian_actor_formation_commands_remain_locked(self):
        self.g.TestUnit(0, 7, 9)
        for kind in (1, 2, 13, 17, 18):
            civilian = self.g.TestUnit(kind, 7, 100 + kind)
            self.assertFalse(self.g.UnitManager.RequestCommand(civilian, 10, self.lua.table_from({'owner': 7, 'id': 9})))
            self.assertFalse(self.g.UnitManager.CanStartCommand(civilian, 10, self.lua.table_from({'owner': 7, 'id': 9})))
        self.assertEqual(self.w.unitCalls, 0)

    def test_military_formation_preserves_nil_false_arguments_and_return_arity(self):
        army = self.g.TestUnit(0, 7, 9)
        self.w.expectedArmy = army
        self.lua.execute("""
          TestGuard.nativeUnit.RequestCommand=function(unit,command,...)
            assert(unit==TestGuard.expectedArmy and command==10 and select('#',...)==3)
            local params,extra,last=...
            assert(params==nil and extra==false and last==nil)
            TestGuard.unitCalls=TestGuard.unitCalls+1
            return nil,false,'native_target_rejected',nil
          end
        """)
        self.assertEqual(self.g.UnitManager.RequestCommand(army, 10, None, False, None), (None, False, 'native_target_rejected', None))
        self.assertEqual(self.w.unitCalls, 1)

    def test_military_command_without_optional_params_keeps_native_arity(self):
        army = self.g.TestUnit(0, 7, 9)
        self.w.expectedArmy = army
        self.lua.execute("""
          TestGuard.nativeUnit.RequestCommand=function(unit,command,...)
            assert(unit==TestGuard.expectedArmy and command==55 and select('#',...)==0)
            TestGuard.unitCalls=TestGuard.unitCalls+1
            return true,'native_no_optional_arguments'
          end
        """)
        self.assertEqual(self.g.UnitManager.RequestCommand(army, 55), (True, 'native_no_optional_arguments'))
        self.assertEqual(self.w.unitCalls, 1)

    def test_city_production_purchase_and_citizens_blocked_but_city_combat_allowed(self):
        city = self.g.TestCity(7)
        self.assertFalse(self.g.CityManager.RequestOperation(city, 99))
        self.assertFalse(self.g.CityManager.RequestCommand(city, 22))
        self.assertFalse(self.g.CityManager.CanStartOperation(city, 99))
        self.assertFalse(self.g.CityManager.CanStartCommand(city, 22))
        self.assertTrue(self.g.CityManager.RequestCommand(city, 20))
        self.assertTrue(self.g.CityManager.RequestCommand(city, 21))
        self.assertEqual(self.w.cityCalls, 2)

    def test_manual_research_and_policies_blocked_but_city_confirmation_allowed(self):
        self.assertFalse(self.g.UI.RequestPlayerOperation(7, 31, self.lua.table()))
        self.lua.execute('Players[7]:GetCulture():RequestPolicyChanges({},{});Players[7]:GetCulture():RequestChangeGovernment(8)')
        self.assertEqual(self.w.cultureCalls, 0)
        valid = self.lua.table_from({'OnStart': 'BaiqiRequisition', 'confirmed': True, 'kind': 'city'})
        self.assertTrue(self.g.UI.RequestPlayerOperation(7, 30, valid))
        valid.kind = 'granary'
        self.assertFalse(self.g.UI.RequestPlayerOperation(7, 30, valid))
        self.assertEqual(self.w.playerCalls, 1)

    def test_native_colon_self_and_multiple_returns_survive_player_proxy(self):
        self.assertEqual(self.lua.eval('function() return Players[7]:GetTreasury() end')(), ('treasury', 17))
        self.assertEqual(self.lua.eval('function() return Players[7]:GetCulture():GetSlotPolicy(3) end')(), (3, 42))

    def test_other_leader_and_other_players_remain_native(self):
        self.w.leader = 'LEADER_TRAJAN'
        builder = self.g.TestUnit(1, 7, 8)
        self.assertEqual(self.g.UnitManager.RequestOperation(builder, 99), (True, 'native'))
        self.assertTrue(self.g.CityManager.RequestOperation(self.g.TestCity(7), 99))
        self.assertTrue(self.g.UI.RequestPlayerOperation(7, 31, self.lua.table()))
        self.lua.execute('Players[7]:GetCulture():RequestChangeGovernment(8)')
        self.assertEqual((self.w.unitCalls, self.w.cityCalls, self.w.playerCalls, self.w.cultureCalls), (1, 1, 1, 1))



    def test_unblocked_culture_reads_do_not_query_write_authority(self):
        self.lua.execute("""
          local culture=Players[7]:GetCulture()
          BaiqiUIGuard.PlayerID=function() error('Readonly native method must not query write authority') end
          for i=1,903 do local slot,value=culture:GetSlotPolicy(i);assert(slot==i and value==42) end
        """)
        self.assertEqual(self.w.cultureCalls,0)

    def test_cached_culture_writes_recheck_current_authority(self):
        self.lua.execute("""
          local culture=Players[7]:GetCulture()
          assert(culture:RequestChangeGovernment(8)==false)
          TestGuard.leader='LEADER_TRAJAN';culture:RequestChangeGovernment(9)
          TestGuard.leader='LEADER_BAIQI';assert(culture:RequestChangeGovernment(8)==false)
          TestGuard.human=false;culture:RequestChangeGovernment(10)
          TestGuard.human=true;assert(culture:RequestChangeGovernment(8)==false)
          TestGuard.multi=true;culture:RequestChangeGovernment(11)
          TestGuard.multi=false;assert(culture:RequestChangeGovernment(8)==false)
        """)
        self.assertEqual(self.w.cultureCalls,3)

if __name__ == '__main__':
    unittest.main()
