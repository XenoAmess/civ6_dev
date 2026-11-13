import copy
import unittest

from tests.observed_capture_fixture import make_bounded_capture
from tools.analyze_observed_capture import analyze_capture


def fixture():
    data = make_bounded_capture()
    phases = []
    for key, offset in [('Core', 100), ('UI', 0)]:
        data['rows'].append(['TIMING_CONTROL', key, '12', 'true'])
        for turn in range(85, 91):
            start = 1 if turn == 85 else 21 + (turn - 86) * 20
            for enabled, at in [(False, start), (True, start + 1)]:
                phases.append({'key': key, 'turn': turn, 'timing_enabled': enabled,
                               'local_before': at + offset, 'local_after': at + offset,
                               'recording': True, 'subscribed': True, 'retired': False})
    return dict(data, timing_phases=phases)


class TimingCoverageTests(unittest.TestCase):
    def rejected(self, data):
        with self.assertRaises(ValueError):
            analyze_capture(**data)

    def test_complete_outside_window_pairs_preserve_actual_write_budget(self):
        result = analyze_capture(**fixture())
        self.assertEqual((result['timing_coverage']['contexts'], result['timing_coverage']['phase_rows']), (2, 24))
        self.assertTrue(result['timing_coverage']['coverage_ok'])
        self.assertAlmostEqual(result['windows'][0]['observed_union_ms'], 3, delta=1e-8)
        self.assertFalse(result['observed_n_req_budget_ok'])
        self.assertEqual(result['complete_turn_writes'][0]['calls'], 70)
        self.assertEqual(result['configured_retained_sample_budget'], 2)

    def test_full_timing_defaults_allow_no_phases_but_changed_control_requires_them(self):
        data = make_bounded_capture()
        data['rows'] += [['TIMING_CONTROL', k, '0', 'true'] for k in data['expected_keys']]
        self.assertNotIn('timing_coverage', analyze_capture(**data))
        data['rows'][-1][2] = '2'
        self.rejected(data)

    def test_missing_duplicate_false_or_mismatched_transition_controls_reject(self):
        for kind in ('missing', 'duplicate', 'false', 'mismatch', 'none'):
            with self.subTest(kind=kind):
                data = fixture()
                row = next(r for r in data['rows'] if r[0] == 'TIMING_CONTROL')
                if kind == 'missing': data['rows'].remove(row)
                elif kind == 'duplicate': data['rows'].append(list(row))
                elif kind == 'false': row[3] = 'false'
                elif kind == 'mismatch': row[2] = '11'
                else: data['rows'] = [r for r in data['rows'] if r[0] != 'TIMING_CONTROL']
                self.rejected(data)

    def test_missing_duplicate_unknown_or_unordered_phases_reject(self):
        for kind in ('missing', 'duplicate', 'unknown', 'turn', 'order', 'flag'):
            with self.subTest(kind=kind):
                data = fixture(); p = data['timing_phases']
                if kind == 'missing': p.pop()
                elif kind == 'duplicate': p[-1] = copy.deepcopy(p[-2])
                elif kind == 'unknown': p[-1]['key'] = 'missing'
                elif kind == 'turn': p[-1]['turn'] = 89
                elif kind == 'flag': p[-1]['timing_enabled'] = 1
                else: p[2], p[3] = p[3], p[2]
                self.rejected(data)

    def test_pause_inside_current_window_and_resume_after_next_activation_reject(self):
        for index, at in ((2, 119), (3, 131), (11, 211)):
            with self.subTest(index=index, at=at):
                data = fixture(); p = data['timing_phases'][index]
                p['local_before'] = p['local_after'] = at
                self.rejected(data)

    def test_offset_uncertainty_cannot_hide_boundary_overlap(self):
        data = fixture()
        for b in data['brackets']:
            if b['key'] == 'Core':
                a, c, _ = b['triple']; b['triple'] = [a, c + 0.1, a + 0.2]
        p = data['timing_phases'][2]
        p['local_before'] = p['local_after'] = 120.05
        self.rejected(data)

    def test_clock_and_counter_recording_shapes_reject_without_assuming_work(self):
        for field, value in [('recording', False), ('subscribed', False), ('retired', True),
                             ('local_before', True), ('local_after', float('nan')),
                             ('local_after', -1), ('local_after', 99)]:
            with self.subTest(field=field, value=value):
                data = fixture(); data['timing_phases'][0][field] = value
                self.rejected(data)
        data = fixture()
        for r in data['rows']:
            if r[0] == 'META': r[15] = '0'
            if r[0] == 'WRITE': r[4] = '0'
        self.assertTrue(analyze_capture(**data)['observed_n_req_budget_ok'])

    def test_legacy_unbounded_missing_budget_and_dropped_samples_still_reject(self):
        data = fixture(); data.pop('sample_budget')
        data['rows'] = [r for r in data['rows'] if r[0] != 'ZERO']
        self.rejected(data)
        data = fixture(); next(r for r in data['rows'] if r[0] == 'META')[3] = '1'
        self.rejected(data)


if __name__ == '__main__':
    unittest.main()
