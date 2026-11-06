"""Behavioral contracts for bounded metadata and Core initialization, no game orders."""
import json
from pathlib import Path
import unittest
from lupa.lua53 import LuaRuntime

ROOT=Path(__file__).resolve().parents[1]

class SettlementStateContracts(unittest.TestCase):
    def check_contracts(self, name, expected, core=False):
        data=json.loads((ROOT/f'tests/fixtures/settlement_{name}_cases.json').read_text(encoding='utf-8'))
        self.assertEqual(len(data['cases']),expected)
        for label,body in data['cases'].items():
            with self.subTest(case=label):
                lua=LuaRuntime()
                lua.execute((ROOT/'mod/Baiqi/Lua/BaiqiSettlementJournal.lua').read_text(encoding='utf-8'))
                lua.execute(data['fixture_lua'])
                if core:lua.execute((ROOT/'mod/Baiqi/Lua/BaiqiSettlementStateCore.lua').read_text(encoding='utf-8'))
                self.assertIs(lua.execute('return(function()'+body+' end)()'),True)

    def test_eighteen_journal_contracts(self):
        self.check_contracts('journal',18)

    def test_twenty_seven_core_storage_contracts(self):
        self.check_contracts('state_core',27,core=True)

if __name__=='__main__':unittest.main()
