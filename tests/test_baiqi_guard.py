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
        for name in ('BaiqiConfig', 'BaiqiUIGuard'):
            self.lua.execute((ROOT / f'mod/Baiqi/Lua/{name}.lua').read_text(encoding='utf-8'))
        self.g, self.w = self.lua.globals(), self.lua.globals().TestGuard

    def test_builder_settler_trader_all_manual_command_sinks_and_hotkey_capability_blocked(self):
        for kind in (1, 2, 3):
            unit = self.g.TestUnit(kind, 7, kind)
            for name in ('RequestOperation', 'RequestCommand', 'CanStartOperation', 'CanStartCommand'):
                self.assertFalse(self.g.UnitManager[name](unit, 99, self.lua.table()))
        self.assertEqual(self.w.unitCalls, 0)

    def test_army_native_identity_arguments_and_multi_return_are_preserved(self):
        army = self.g.TestUnit(0, 7, 9)
        self.assertEqual(self.g.UnitManager.RequestOperation(army, 55, self.lua.table()), (True, 'native'))
        self.assertEqual(self.w.lastUnit.GetID(), 9)
        self.assertEqual((self.w.unitCalls, self.w.lastAction), (1, 55))

    def test_civilian_escort_join_cannot_bypass_guard_via_army(self):
        army = self.g.TestUnit(0, 7, 9)
        self.g.TestUnit(1, 7, 8)
        self.assertFalse(self.g.UnitManager.RequestCommand(army, 10, self.lua.table_from({'owner': 7, 'id': 8})))
        self.assertEqual(self.w.unitCalls, 0)

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


if __name__ == '__main__':
    unittest.main()
