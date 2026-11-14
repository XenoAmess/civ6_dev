from pathlib import Path
from unittest.mock import patch
import io
import contextlib
import tempfile
import unittest
from lupa.lua51 import LuaRuntime
from tools import build_plan_profile_mod as builder

ROOT=Path(__file__).resolve().parents[1]


class BuildPressurePlanTests(unittest.TestCase):
    def setUp(self):
        self.raw=(ROOT/'mod/Baiqi'/builder.EXECUTOR).read_text(encoding='utf-8')

    def instance(self,prefix):
        lua=LuaRuntime(unpack_returned_tuples=True)
        lua.execute('Game={};Players={};Automation={};Events={PlayerTurnActivated={Add=function()end,Remove=function()end}}')
        lua.execute(prefix);return lua.globals().P6PerfPlanA

    def test_pressure_prefix_constructs_actual_metadata_and_exact_inverse(self):
        for t in (0,210,2147483641):
            text,prefix,binding=builder.transform(self.raw,142,pressure_initial_turn=t)
            self.assertEqual(builder.restore_release(text,prefix,binding),self.raw)
            h=self.instance(prefix)
            self.assertEqual(h.source,'baiqi142-pressure-stageA-v1')
            self.assertEqual((h.initialTurn,h.planFirstTurn,h.planLastTurn),(t,t+1,t+5))
            self.assertEqual(h.profile.capacity,4096)
            self.assertFalse(h.profile.aggregateZero)

    def test_default_constructor_keeps_legacy_source_and_calendar(self):
        text,prefix,binding=builder.transform(self.raw,142)
        self.assertEqual(builder.restore_release(text,prefix,binding),self.raw)
        h=self.instance(prefix)
        self.assertEqual(h.source,'baiqi142-stageA-v2')
        self.assertIsNone(h.initialTurn)
        self.assertEqual((h.planFirstTurn,h.planLastTurn),(86,90))

    def test_invalid_pressure_types_and_source_rejected_before_output(self):
        for bad in (True,False,-1,1.5,'0',2147483642):
            with self.subTest(bad=bad),self.assertRaises(ValueError):
                builder.transform(self.raw,142,pressure_initial_turn=bad)
        with self.assertRaises(ValueError):builder.transform(self.raw,140,pressure_initial_turn=0)
        output=Path(tempfile.mkdtemp(prefix='pressure-invalid-',dir=ROOT/'.local-model'))/'never-created'
        self.assertTrue(output.resolve().is_relative_to((ROOT/'.local-model').resolve()))
        with patch.object(builder,'manifest_files',return_value=[]):
            with self.assertRaises(ValueError):builder.build(output,pressure_initial_turn=True)
        self.assertFalse(output.exists())

    def test_cli_passes_explicit_calendar_to_builder(self):
        argv=['build_plan_profile_mod.py','--output-dir','unused-pressure-output','--pressure-initial-turn','210']
        with patch('sys.argv',argv),patch.object(builder,'build',return_value={})as call,contextlib.redirect_stdout(io.StringIO()):
            builder.main()
        call.assert_called_once_with(Path('unused-pressure-output'),pressure_initial_turn=210)


if __name__=='__main__':unittest.main()
