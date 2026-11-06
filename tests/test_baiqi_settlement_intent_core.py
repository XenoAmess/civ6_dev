"""A durable ACK can grant once; uncertainty never authorizes another order."""
import json
from pathlib import Path
import unittest
from lupa.lua53 import LuaRuntime

ROOT=Path(__file__).resolve().parents[1]

class SettlementIntentCoreContracts(unittest.TestCase):
    def test_persistent_authorization_and_effect_boundaries(self):
        data=json.loads((ROOT/'tests/fixtures/settlement_intent_core_cases.json').read_text(encoding='utf-8'))
        for label,body in data['cases'].items():
            with self.subTest(case=label):
                lua=LuaRuntime()
                for name in ('BaiqiSettlementJournal','BaiqiSettlementStateCore','BaiqiSettlementIntentCore'):
                    lua.execute((ROOT/f'mod/Baiqi/Lua/{name}.lua').read_text(encoding='utf-8'))
                lua.execute(data['fixture_lua'])
                self.assertIs(lua.execute('return(function()'+body+' end)()'),True)

if __name__=='__main__':unittest.main()
