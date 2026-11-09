"""Real early-save diagnostic scope, without changing gameplay or clocks."""
from pathlib import Path
import os
import unittest
from lupa.lua51 import LuaRuntime
from test_diagnostic_prophet_supply import FIXTURE

ROOT=Path(__file__).resolve().parents[1]


class EarlyProphetSupplyTests(unittest.TestCase):
    def read(self,turn,granted=0):
        lua=LuaRuntime(unpack_returned_tuples=True)
        lua.execute(FIXTURE)
        lua.globals().W.turn=turn
        lua.globals().W.past[1].TurnGranted=granted
        source=Path(os.environ.get('BAIQI_PROPHET_SUPPLY_SOURCE') or ROOT/'tools/lua/diagnostic_prophet_supply.lua')
        result=lua.execute(source.read_text(encoding='utf-8')).Read(lua.globals().E)
        self.assertEqual(lua.globals().W.writes,0)
        return result

    def test_supported_early_and_original_boundaries(self):
        for turn in (99,149,150,250):
            with self.subTest(turn=turn):
                result=self.read(turn)
                self.assertEqual(result.status,'KNOWN')
                self.assertEqual(result.turn,turn)

    def test_turns_outside_the_explicit_window_remain_unknown(self):
        for turn in (98,251):
            with self.subTest(turn=turn):
                self.assertEqual(self.read(turn).status,'UNKNOWN')

    def test_past_records_cannot_claim_a_future_or_negative_turn(self):
        for turn in (99,150,250):
            with self.subTest(turn=turn):
                self.assertEqual(self.read(turn,turn).status,'KNOWN')
                self.assertEqual(self.read(turn,turn+1).status,'UNKNOWN')
                self.assertEqual(self.read(turn,-1).status,'UNKNOWN')


if __name__=='__main__':
    unittest.main()
