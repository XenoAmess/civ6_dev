import copy
import unittest
from tools.analyze_plan_capture import analyze_plan_capture, analyze_pressure_plan_capture
from test_analyze_plan_capture import capture
from test_analyze_plan_preanchor import v2, add_pre

class PressureAnalyzerTests(unittest.TestCase):
    def _pressure(self, T=210):
        d = capture()
        d['source'] = 'baiqi142-pressure-stageA-v1'
        d['initial_turn'] = T
        d['closing_actual_turn'] = T + 6
        d['pre_anchor'] = {'pending': 0, 'recorded': 0, 'validated': 0, 'errors': 0}
        d['anchors'] = {str(t): 10. + 20 * (t - (T + 1)) for t in range(T + 1, T + 7)}
        d['samples'] = []
        for name in ('Admin.Run', 'Controller.RunNow'):
            for t in range(T + 1, T + 6):
                a = d['anchors'][str(t)]
                for i in range(20):
                    st = a + .02 * i; en = st + .001
                    d['samples'].append({'name': name, 'seconds': en - st, 'failed': False,
                        'started': st, 'ended': en, 'turnStart': t, 'turnEnd': t,
                        'cityStart': 10, 'cityEnd': 10, 'anchor': a, 'windowEligible': True,
                        'preAnchor': False, 'argumentCount': 0, 'allowOrders': 'nil'})
        d['profile']['total_calls'] = len(d['samples'])
        return d

    def test_valid_pressure_fixture(self):
        d = self._pressure(210)
        s = analyze_pressure_plan_capture(d)
        self.assertEqual(s['initial_turn'], 210)
        self.assertEqual(s['targets']['Admin.Run']['pure_ten_count'], 100)
        self.assertTrue(s['overall_budget_ok'])

    def test_invalid_initial_turn(self):
        d = self._pressure(210)
        d['initial_turn'] = True
        with self.assertRaises(ValueError): analyze_pressure_plan_capture(d)
        d = self._pressure(210)
        d['initial_turn'] = 2147483642
        with self.assertRaises(ValueError): analyze_pressure_plan_capture(d)

    def test_legacy_rejects_pressure(self):
        d = self._pressure(210)
        with self.assertRaises(ValueError): analyze_plan_capture(d)

    def test_pressure_rejects_legacy(self):
        d = capture()
        with self.assertRaises(ValueError): analyze_pressure_plan_capture(d)

    def test_preanchor_and_immutability(self):
        d = self._pressure(0)
        add_pre(d)
        d["samples"][-1].update(turnStart=d["initial_turn"]+1,turnEnd=d["initial_turn"]+1)
        before = copy.deepcopy(d)
        s = analyze_pressure_plan_capture(d)
        self.assertEqual(d, before)
        self.assertEqual(s['pre_anchor']['validated'], 1)
        self.assertEqual(s['classification_counts']['Controller.RunNow']['before_native_anchor'], 1)

    def test_invalid_closing_turn(self):
        d = self._pressure(210)
        d['closing_actual_turn'] = 215
        with self.assertRaises(ValueError): analyze_pressure_plan_capture(d)

    def test_actual_zero_and_upper_boundary_turn_labels(self):
        for T in (0, 2147483641):
            d = self._pressure(T); before = copy.deepcopy(d)
            s = analyze_pressure_plan_capture(d)
            self.assertEqual(d, before)
            self.assertEqual(s['initial_turn'], T)
            self.assertEqual(set(s['eligible_calls_by_turn']['Admin.Run']), {str(t) for t in range(T+1,T+6)})
            self.assertTrue(s['overall_budget_ok'])

    def test_excluded_slow_rows_do_not_fill_pure_ten_minimum(self):
        d = self._pressure(0); d['samples'][0].update(cityEnd=11,seconds=1.,ended=d['samples'][0]['started']+1.)
        add_pre(d);d['samples'][-1].update(turnStart=1,turnEnd=1)
        s = analyze_pressure_plan_capture(d)
        self.assertEqual(s['targets']['Admin.Run']['pure_ten_count'],99)
        self.assertFalse(s['targets']['Admin.Run']['budget_ok'])
        self.assertEqual(s['targets']['Controller.RunNow']['pure_ten_count'],100)
        self.assertLess(s['targets']['Controller.RunNow']['max_ms'],2)

    def test_unknown_quality_clock_and_anchor_are_rejected(self):
        for edit in (lambda d:d['pre_anchor'].update(pending=1),
                     lambda d:d['profile'].update(dropped=1),
                     lambda d:d['profile'].update(capacity=8192),
                     lambda d:d['samples'][0].update(started=float('nan')),
                     lambda d:d['samples'][0].update(turnStart=86),
                     lambda d:d['samples'][0].update(anchor=0),
                     lambda d:d['samples'][0].update(windowEligible=False)):
            d=self._pressure(210);edit(d)
            with self.assertRaises(ValueError):analyze_pressure_plan_capture(d)

if __name__ == '__main__':
    unittest.main()