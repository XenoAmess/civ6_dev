"""Bounded, detached movement proposal schema; no game objects or effects."""
from pathlib import Path
import json
import unittest
from lupa.lua51 import LuaRuntime

ROOT=Path(__file__).resolve().parents[1]


class SettlerGoalsSchemaTests(unittest.TestCase):
    def test_proposal_data_contracts(self):
        cases=json.loads((ROOT/'tests/fixtures/settler_goals_schema_cases.json').read_text(encoding='utf-8'))
        source=(ROOT/'mod/Baiqi/Lua/BaiqiSettlerGoals.lua').read_text(encoding='utf-8')
        for name,body in cases.items():
            with self.subTest(case=name):
                lua=LuaRuntime();lua.globals().M=lua.execute(source)
                self.assertIsNotNone(lua.globals().BaiqiSettlerGoals)
                self.assertTrue(lua.execute(body))


if __name__=='__main__':unittest.main()
