"""The census observes pending topology without turning it into a rejected site."""
from pathlib import Path
import unittest
from unittest.mock import patch
from lupa.lua51 import LuaRuntime as L51
from lupa.lua53 import LuaRuntime as L53
from tools.build_settlement_census_mod import transform, restore_release, EDITS, EDITS_167
from tools.analyze_settlement_census import classify_settlement_call
from tests import test_support_geometry_slices as geometry

ROOT=Path(__file__).resolve().parents[1]
CONTROLLER=ROOT/'mod/Baiqi/Lua/BaiqiController.lua'

class SupportGeometryCensusTests(unittest.TestCase):
 def test_current_shape_recovers_exactly_for_current_and_legacy_labels(self):
  raw=CONTROLLER.read_text(encoding='utf-8')
  for version in(142,155,167):
   text,prefix=transform(raw,source_version=version)
   self.assertEqual(restore_release(text,prefix),raw)
   self.assertIn(f'natural source{version} settlement census',prefix)
   self.assertEqual(text.count(EDITS_167[5][1]),1)
 def test_duplicate_and_missing_pending_anchors_never_fall_back_to_legacy(self):
  raw=CONTROLLER.read_text(encoding='utf-8');anchor=EDITS_167[5][0]
  for invalid in(raw+anchor,raw.replace(anchor,'missing',1),raw+EDITS[5][0]):
   with self.assertRaises(ValueError):transform(invalid,source_version=167)
  text,prefix=transform(raw,source_version=167)
  with self.assertRaises(ValueError):restore_release(text+EDITS_167[5][1],prefix)
 def test_actual_cold_pending_census_keeps_original_controller_progress(self):
  raw=CONTROLLER.read_text(encoding='utf-8');text,_=transform(raw,source_version=167);read=Path.read_text
  def observed(path,*args,**kwargs):return text if path.resolve()==CONTROLLER else read(path,*args,**kwargs)
  for E in(L51,L53):
   helper=geometry.SupportGeometryTests();baseline=helper.world(E)
   with patch.object(Path,'read_text',observed):instrumented=helper.world(E)
   helper.step(baseline);helper.step(instrumented)
   rows=instrumented.lua.globals().P6SettlementCensus.Snapshot().rows
   self.assertEqual(len(rows),1);self.assertEqual(rows[1].support_unknown,1)
   classified=classify_settlement_call(dict(rows[1].items()));self.assertIsNot(classified['global_no_legal_site'],True)
   for _ in range(80):
    self.assertEqual(helper.calls(baseline),helper.calls(instrumented))
    self.assertEqual(len(baseline.w.unitRequests),len(instrumented.w.unitRequests))
    if helper.moves(baseline):break
    helper.step(baseline);helper.step(instrumented)
   self.assertEqual(len(helper.moves(baseline)),1);self.assertEqual(len(helper.moves(instrumented)),1)

if __name__=='__main__':unittest.main()
