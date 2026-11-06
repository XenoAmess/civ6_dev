"""Identity and visible-world failures cannot become settlement completion facts."""
import json
from pathlib import Path
import unittest
from lupa.lua53 import LuaRuntime

ROOT=Path(__file__).resolve().parents[1]

class SettlementWorldContracts(unittest.TestCase):
    def check_component(self,name,source):
        fixture=json.loads((ROOT/f'tests/fixtures/settlement_{name}_cases.json').read_text(encoding='utf-8'))
        for label,body in fixture['cases'].items():
            with self.subTest(case=label):
                lua=LuaRuntime()
                lua.execute((ROOT/'mod/Baiqi/Lua/BaiqiSettlementJournal.lua').read_text(encoding='utf-8'))
                lua.execute(fixture['fixture_lua'])
                lua.execute((ROOT/f'mod/Baiqi/Lua/{source}.lua').read_text(encoding='utf-8'))
                self.assertIs(lua.execute('return(function()'+body+' end)()'),True)

    def test_settler_identity_and_consumption_boundaries(self):
        self.check_component('unit_core','BaiqiSettlementUnitCore')

    def test_known_visible_tile_boundaries(self):
        self.check_component('tile_core','BaiqiSettlementTileCore')

if __name__=='__main__':unittest.main()
