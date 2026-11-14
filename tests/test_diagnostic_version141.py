"""Version provenance must be explicit at each diagnostic/action boundary."""
import unittest
from test_analyze_plan_capture import capture
from test_paired_normal_driver import NormalHarness,execute
from tools.analyze_plan_capture import analyze_plan_capture
from tools.build_controller_diagnostic import suffix
from tools.build_plan_profile_mod import transform,ROOT,EXECUTOR
from tools.paired_normal_end import request_end


class DiagnosticVersion141Tests(unittest.TestCase):
    def test_plan_analyzer_rejects_other_version_and_retains_thresholds(self):
        d=capture();d['source']='baiqi141-stageA-v1'
        with self.assertRaises(ValueError):analyze_plan_capture(d)
        self.assertTrue(analyze_plan_capture(d,expected_source_version=141)['overall_budget_ok'])
        row=d['samples'][0];row.update(seconds=.051,ended=row['started']+.051)
        self.assertFalse(analyze_plan_capture(d,expected_source_version=141)['overall_budget_ok'])
        d['source']='baiqi140-stageA-v1'
        with self.assertRaises(ValueError):analyze_plan_capture(d,expected_source_version=141)

    def test_explicit141_driver_endpoint_and_bridge_complete_five_ordinary_actions(self):
        h=NormalHarness(source_version=141)
        h.lua.execute('Game.IsAllowStrategicCommands=function()return true end;UI.CanEndTurn=function()return true end')
        result=execute(h,lambda turn,token:request_end(h.query,turn,token,expected_source_version=141),expected_source_version=141)
        self.assertEqual(result['source_version'],141)
        self.assertEqual(list(h.t.actions.values()),list(range(85,90)))
        self.assertEqual([r['seconds']for r in result['records']],[2]*5)
        self.assertFalse((h.ledger/'end-90.json').exists())

    def test_bridge_rejects_mismatched_stage_before_clock_or_action(self):
        h=NormalHarness(source_version=141)
        h.lua.execute("P6PairStage={phase='RECORDING',token=string.rep('b',32),normal_end=true,source_version=140,ends={[85]=true}}")
        self.assertFalse(h.lua.eval("ExposedMembers.P6BaiqiPairEndBridge.Begin(85,string.rep('b',32))"))
        self.assertIsNone(h.lua.eval('P6PairClock:Snapshot().pending'))
        self.assertEqual(len(h.t.actions),0)

    def test_wrong_driver_version_aborts_without_game_action(self):
        h=NormalHarness(source_version=141)
        with self.assertRaises(Exception):execute(h)
        self.assertEqual(len(h.t.actions),0)
        self.assertIsNone(h.lua.eval('P6PairStage'))
        self.assertTrue(h.lua.eval('P6PairEndOwner.active'))
        self.assertIn('PAIR_ABORT_RETIRE_RECEIPT ["SKIPPED_FOREIGN"]',h.messages)

    def test_explicit142_endpoint_and_capture_labels_remain_version_bound(self):
        h=NormalHarness(source_version=142)
        h.lua.execute('Game.IsAllowStrategicCommands=function()return true end;UI.CanEndTurn=function()return true end')
        result=execute(h,lambda turn,token:request_end(h.query,turn,token,expected_source_version=142),expected_source_version=142)
        self.assertEqual(result['source_version'],142)
        self.assertEqual(list(h.t.actions.values()),list(range(85,90)))
        from tools.analyze_paired_turns import validate_capture_mode
        validate_capture_mode(result,142,True)
        with self.assertRaises(ValueError):validate_capture_mode(result,141,True)
        d=capture();d['source']='baiqi142-stageA-v1'
        self.assertTrue(analyze_plan_capture(d,expected_source_version=142)['overall_budget_ok'])
        with self.assertRaises(ValueError):analyze_plan_capture(d,expected_source_version=141)

    def test_unknown_versions_rejected_before_output_ledger_or_query(self):
        raw=(ROOT/'mod/Baiqi'/EXECUTOR).read_text(encoding='utf-8')
        for value in (None,True,140.,141.,143,'141'):
            with self.subTest(value=value):
                with self.assertRaises(ValueError):suffix(source_version=value)
                with self.assertRaises(ValueError):transform(raw,value)
                with self.assertRaises(ValueError):analyze_plan_capture(capture(),expected_source_version=value)
                calls=[]
                with self.assertRaises(ValueError):request_end(lambda *a:calls.append(a),85,'b'*32,expected_source_version=value)
                self.assertFalse(calls)
                h=NormalHarness()
                with self.assertRaises(ValueError):execute(h,expected_source_version=value)
                self.assertFalse(h.ledger.exists());self.assertEqual(len(h.t.actions),0)


if __name__=='__main__':unittest.main()
