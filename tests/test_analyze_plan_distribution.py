import copy
import unittest
from tools.analyze_plan_capture import analyze_plan_capture
from test_analyze_plan_capture import capture
from test_analyze_plan_preanchor import v2, add_pre


class AnalyzePlanDistributionTests(unittest.TestCase):
    def test_even_n_nearest_rank_p50_and_p95(self):
        d = capture()
        # Modify Admin.Run samples to have distinct durations: 1ms to 100ms
        # We need 100 samples for Admin.Run. capture() creates 20 per turn * 5 turns = 100.
        # Let's set them to 1, 2, ..., 100 ms.
        idx = 0
        for r in d['samples']:
            if r['name'] == 'Admin.Run':
                r['seconds'] = (idx + 1) / 1000.0
                r['ended'] = r['started'] + r['seconds']
                idx += 1
        s = analyze_plan_capture(d)
        t = s['targets']['Admin.Run']
        self.assertEqual(t['pure_ten_count'], 100)
        # n=100. p50 rank = ceil(0.5*100)-1 = 50-1 = 49 (0-indexed). Value is 50ms.
        self.assertEqual(t['p50_ms'], 50.0)
        # p95 rank = ceil(0.95*100)-1 = 95-1 = 94 (0-indexed). Value is 95ms.
        self.assertEqual(t['p95_ms'], 95.0)
        self.assertEqual(t['max_ms'], 100.0)
        self.assertEqual(t['above_20ms_count'], 80) # 21..100
        self.assertEqual(t['above_50ms_count'], 50) # 51..100
        self.assertFalse(t['budget_ok']) # p95 > 20

    def test_strict_overrun_boundary_and_exact_values(self):
        d = capture()
        # Set all Admin.Run samples to exactly 20ms
        for r in d['samples']:
            if r['name'] == 'Admin.Run':
                r['seconds'] = 0.020
                r['ended'] = r['started'] + r['seconds']
        s = analyze_plan_capture(d)
        t = s['targets']['Admin.Run']
        self.assertEqual(t['p50_ms'], 20.0)
        self.assertEqual(t['p95_ms'], 20.0)
        self.assertEqual(t['max_ms'], 20.0)
        self.assertEqual(t['above_20ms_count'], 0) # Strictly > 20
        self.assertEqual(t['above_50ms_count'], 0)
        self.assertTrue(t['budget_ok']) # p95 <= 20, max <= 50

        # Set all Admin.Run samples to exactly 50ms
        for r in d['samples']:
            if r['name'] == 'Admin.Run':
                r['seconds'] = 0.050
                r['ended'] = r['started'] + r['seconds']
        s = analyze_plan_capture(d)
        t = s['targets']['Admin.Run']
        self.assertEqual(t['p50_ms'], 50.0)
        self.assertEqual(t['p95_ms'], 50.0)
        self.assertEqual(t['max_ms'], 50.0)
        self.assertEqual(t['above_20ms_count'], 100) # All > 20
        self.assertEqual(t['above_50ms_count'], 0) # None > 50
        self.assertFalse(t['budget_ok']) # p95 > 20

    def test_exclusion_and_empty_set_semantics(self):
        d = capture()
        # Remove all Admin.Run samples to test empty set behavior
        d['samples'] = [r for r in d['samples'] if r['name'] != 'Admin.Run']
        d['profile']['total_calls'] = len(d['samples'])
        s = analyze_plan_capture(d)
        t = s['targets']['Admin.Run']
        self.assertEqual(t['pure_ten_count'], 0)
        self.assertIsNone(t['p50_ms'])
        self.assertIsNone(t['p95_ms'])
        self.assertIsNone(t['max_ms'])
        self.assertEqual(t['above_20ms_count'], 0)
        self.assertEqual(t['above_50ms_count'], 0)
        self.assertFalse(t['budget_ok']) # n < 100

        # Test that excluded categories (e.g., 10_to_11) do not affect counts
        d = capture()
        # Change one Admin.Run sample to 10_to_11
        for r in d['samples']:
            if r['name'] == 'Admin.Run':
                r['cityEnd'] = 11
                break
        s = analyze_plan_capture(d)
        t = s['targets']['Admin.Run']
        self.assertEqual(t['pure_ten_count'], 99)
        self.assertEqual(t['above_20ms_count'], 0) # Original samples were ~1ms
        self.assertEqual(t['above_50ms_count'], 0)

    def test_input_immutability_and_legacy_budget(self):
        d = capture()
        before = copy.deepcopy(d)
        s = analyze_plan_capture(d)
        self.assertEqual(d, before)
        # Verify legacy budget_ok semantics unchanged
        t = s['targets']['Admin.Run']
        self.assertTrue(t['budget_ok'])
        self.assertAlmostEqual(t['p50_ms'], 1.0, places=9) # All samples 1ms
        self.assertAlmostEqual(t['p95_ms'], 1.0, places=9)
        self.assertAlmostEqual(t['max_ms'], 1.0, places=9)
        self.assertEqual(t['above_20ms_count'], 0)
        self.assertEqual(t['above_50ms_count'], 0)

    def test_rare_slow_call_does_not_replace_the_p95_budget(self):
        d = capture()
        row = d['samples'][0]
        row.update(seconds=.050, ended=row['started'] + .050)
        t = analyze_plan_capture(d)['targets']['Admin.Run']
        self.assertAlmostEqual(t['p50_ms'], 1., places=9)
        self.assertAlmostEqual(t['p95_ms'], 1., places=9)
        self.assertEqual(t['max_ms'], 50.)
        self.assertEqual(t['above_20ms_count'], 1)
        self.assertEqual(t['above_50ms_count'], 0)
        self.assertTrue(t['budget_ok'])

    def test_all_excluded_classes_stay_out_of_the_distribution(self):
        d = v2()
        add_pre(d)
        edits = [dict(cityEnd=11), dict(cityStart=11, cityEnd=11),
                 dict(turnEnd=87), dict(started=20., windowEligible=False),
                 dict(cityStart=9, cityEnd=9)]
        for row, edit in zip(d['samples'], edits):
            row.update(edit)
            row.update(seconds=1., ended=row['started'] + 1.)
        s = analyze_plan_capture(d)
        classes = s['classification_counts']['Admin.Run']
        for group in ('10_to_11', 'eleven_city', 'turn_crossing',
                      'outside_window', 'other_city_state'):
            self.assertEqual(classes[group], 1)
        self.assertEqual(s['classification_counts']['Controller.RunNow']['before_native_anchor'], 1)
        for name, n in (('Admin.Run', 95), ('Controller.RunNow', 100)):
            t = s['targets'][name]
            self.assertEqual(t['pure_ten_count'], n)
            self.assertAlmostEqual(t['p50_ms'], 1., places=9)
            self.assertAlmostEqual(t['max_ms'], 1., places=9)
            self.assertEqual(t['above_20ms_count'], 0)
            self.assertEqual(t['above_50ms_count'], 0)
            self.assertEqual(t['budget_ok'], n >= 100)

if __name__ == '__main__':
    unittest.main()
