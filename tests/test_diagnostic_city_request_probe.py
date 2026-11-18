"""Passive request observation must preserve the real handler's behavior."""
from pathlib import Path
import unittest
from lupa.lua51 import LuaRuntime as L51
from lupa.lua53 import LuaRuntime as L53

R = Path(__file__).resolve().parents[1]


class CityRequestProbeTests(unittest.TestCase):
    def test_forwarding_returns_bounds_and_retirement(self):
        source = (R / 'tools/lua/diagnostic_city_request_probe.lua').read_text(encoding='utf-8')
        fixture = (R / 'tests/lua/mock_city_request_probe.lua').read_text(encoding='utf-8')
        for name, runtime in (('Lua51', L51), ('Lua53', L53)):
            with self.subTest(VM=name):
                lua = runtime()
                lua.globals().New = lua.execute(source)
                self.assertIs(lua.execute(fixture), True)


if __name__ == '__main__':
    unittest.main()
