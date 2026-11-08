"""Information readers preserve unknowns and use actual Lua 5.1 API conventions."""
import json
from pathlib import Path
import unittest

from lupa.lua51 import LuaRuntime

ROOT = Path(__file__).resolve().parents[1]


class LoyaltyInformationTests(unittest.TestCase):
    def run_cases(self, module_name, fixture_name):
        fixture = json.loads(
            (ROOT / "tests/fixtures" / fixture_name).read_text(encoding="utf-8")
        )
        source = (ROOT / "tools/lua" / module_name).read_text(encoding="utf-8")
        for name, check in fixture["cases"].items():
            with self.subTest(case=name):
                lua = LuaRuntime(unpack_returned_tuples=True)
                lua.execute(fixture["fixture"])
                lua.globals().M = lua.execute(source)
                lua.execute(check)

    def test_settlement_warning_actual_receivers_visibility_and_unknown_entries(self):
        self.run_cases("settlement_warning_info.lua", "settlement_warning_info_cases.json")

    def test_own_age_actual_receivers_consistency_and_unknown_values(self):
        self.run_cases("own_age_info.lua", "own_age_info_cases.json")


if __name__ == "__main__":
    unittest.main()
