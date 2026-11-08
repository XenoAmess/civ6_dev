from pathlib import Path
import json,unittest
from lupa.lua51 import LuaRuntime
ROOT=Path(__file__).resolve().parents[1]


class CityCommandObserverTests(unittest.TestCase):
    def test_transparent_calls_unknowns_owned_restore_and_rollback_cases(self):
        data=json.loads((ROOT/'tests/fixtures/city_command_observer_cases.json').read_text(encoding='utf-8'))
        source=(ROOT/'tools/lua/diagnostic_city_commands.lua').read_text(encoding='utf-8')
        for name,code in data['cases'].items():
            with self.subTest(case=name):
                lua=LuaRuntime(unpack_returned_tuples=True)
                lua.execute(data['fixture']);lua.globals().M=lua.execute(source);lua.execute(code)
