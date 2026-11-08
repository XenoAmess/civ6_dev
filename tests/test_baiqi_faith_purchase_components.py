import unittest
from pathlib import Path
from lupa.lua51 import LuaRuntime
from missionary_purchase_fixtures import snapshot_fixture,snapshot_cases,guard_fixture,guard_cases
ROOT=Path(__file__).resolve().parents[1]

class FaithPurchaseComponentsTests(unittest.TestCase):
    def test_missionary_core_snapshot_cases(self):
        for name,code in snapshot_cases.items():
            with self.subTest(case=name):
                lua=LuaRuntime();lua.execute(snapshot_fixture)
                lua.globals().M=lua.execute((ROOT/'mod/Baiqi/Lua/BaiqiMissionaryPurchaseSnapshot.lua').read_text(encoding='utf-8'))
                lua.execute(code)

    def test_shared_faith_property_guard_cases(self):
        for name,code in guard_cases.items():
            with self.subTest(case=name):
                lua=LuaRuntime()
                for file in ('BaiqiNaturalistPurchaseJournal','BaiqiMissionaryPurchaseJournal'):
                    lua.execute((ROOT/f'mod/Baiqi/Lua/{file}.lua').read_text(encoding='utf-8'))
                lua.execute(guard_fixture)
                lua.globals().M=lua.execute((ROOT/'mod/Baiqi/Lua/BaiqiFaithPurchaseGuard.lua').read_text(encoding='utf-8'))
                lua.execute(code);self.assertEqual(lua.globals().H.writes,0)
