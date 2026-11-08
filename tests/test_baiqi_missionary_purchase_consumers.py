from pathlib import Path
import unittest
from lupa.lua51 import LuaRuntime
from test_baiqi_missionary_purchase import FIXTURE
from missionary_purchase_ui_fixtures import demand_fixture,demand_cases,submit_fixture,submit_cases
ROOT=Path(__file__).resolve().parents[1]


class MissionaryPurchaseConsumerTests(unittest.TestCase):
    def test_domestic_demand_cases(self):
        for name,(setup,expected)in demand_cases.items():
            with self.subTest(case=name):
                lua=LuaRuntime(unpack_returned_tuples=True);lua.execute(demand_fixture)
                module=lua.execute((ROOT/'mod/Baiqi/Lua/BaiqiMissionaryPurchaseDemand.lua').read_text(encoding='utf-8'))
                lua.execute(setup)
                self.assertIs(module.Read(lua.globals().E,lua.globals().Player,0),expected)
                self.assertEqual(lua.globals().W.foreignReads,0)

    def test_single_submit_and_receipt_cases(self):
        for name,(setup,stage,commands)in submit_cases.items():
            with self.subTest(case=name):
                lua=LuaRuntime(unpack_returned_tuples=True);lua.execute(FIXTURE)
                lua.globals().E.Quote=lua.execute((ROOT/'mod/Baiqi/Lua/BaiqiMissionaryPurchase.lua').read_text(encoding='utf-8'))
                lua.execute(submit_fixture)
                module=lua.execute((ROOT/'mod/Baiqi/Lua/BaiqiMissionaryPurchaseSubmit.lua').read_text(encoding='utf-8'))
                lua.execute(setup)
                self.assertEqual(module.Request(lua.globals().E,0,65536,100)[0],stage)
                self.assertEqual(lua.globals().F.commands,commands)
                module.Request(lua.globals().E,0,65536,100)
                self.assertEqual(lua.globals().F.commands,commands)
                self.assertEqual(lua.globals().F.writes,0)
