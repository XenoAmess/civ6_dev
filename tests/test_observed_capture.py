import unittest
from observed_capture_fixture import make_capture
from tools.analyze_observed_capture import analyze_capture

class TestObservedCapture(unittest.TestCase):
    def test_actual_fixture_structure(self):
        data = make_capture()
        res = analyze_capture(**data)
        self.assertEqual(len(res['windows']), 5)
        self.assertEqual(res['contexts'], 2)
        self.assertEqual(res['samples'], 3)
        self.assertAlmostEqual(res['windows'][0]['observed_union_ms'], 3, delta=1e-8)
        self.assertAlmostEqual(res['windows'][0]['clipped_inclusive_sum_ms_not_cpu'], 4, delta=1e-8)
        self.assertEqual(res['clock_bounds']['Core']['lower_seconds'], 100)
        self.assertTrue(res['observed_b_turn_budget_ok'])
        self.assertFalse(res['observed_n_req_budget_ok'])

    def test_write_budget_boundary(self):
        data = make_capture(ui_calls=44, core_calls=20)
        res = analyze_capture(**data)
        self.assertTrue(res['observed_n_req_budget_ok'])
        data = make_capture(ui_calls=45, core_calls=20)
        res = analyze_capture(**data)
        self.assertFalse(res['observed_n_req_budget_ok'])

    def test_invalid_metadata_fields(self):
        with self.subTest('totalCalls'):
            data = make_capture()
            row = next(r for r in data['rows'] if r[0]=='META')
            row[2] = '2'
            with self.assertRaises(ValueError): analyze_capture(**data)
        with self.subTest('dropped'):
            data = make_capture()
            row = next(r for r in data['rows'] if r[0]=='META')
            row[3] = '1'
            with self.assertRaises(ValueError): analyze_capture(**data)
        with self.subTest('invalidClock'):
            data = make_capture()
            row = next(r for r in data['rows'] if r[0]=='META')
            row[4] = '1'
            with self.assertRaises(ValueError): analyze_capture(**data)
        with self.subTest('counterTotal'):
            data = make_capture()
            row = next(r for r in data['rows'] if r[0]=='META')
            row[15] = '15'
            with self.assertRaises(ValueError): analyze_capture(**data)

    def test_missing_anchor_or_bounds(self):
        with self.subTest('missingCoreMeta'):
            data = make_capture()
            data['rows'] = [r for r in data['rows'] if not (r[0]=='META' and r[1]=='Core')]
            with self.assertRaises(ValueError): analyze_capture(**data)
        with self.subTest('missingClosingAnchor'):
            data = make_capture()
            data['rows'] = [r for r in data['rows'] if not (r[0]=='ANCHOR' and r[1]=='Core' and r[4]=='91')]
            with self.assertRaises(ValueError): analyze_capture(**data)
        with self.subTest('badBounds'):
            data = make_capture()
            data['capture_bounds'] = [0, 109]
            with self.assertRaises(ValueError): analyze_capture(**data)

    def test_duplicate_rows(self):
        with self.subTest('dupSample'):
            data = make_capture()
            data['rows'].append(['SAMPLE','Core','1','X','1','1','0','false'])
            with self.assertRaises(ValueError): analyze_capture(**data)
        with self.subTest('dupWrite'):
            data = make_capture()
            data['rows'].append(['WRITE','Core','86','Property.Call','20'])
            with self.assertRaises(ValueError): analyze_capture(**data)
        with self.subTest('validDupIndex'):
            data = make_capture()
            self.assertEqual(analyze_capture(**data)['samples'], 3)

    def test_failed_or_invalid_samples(self):
        with self.subTest('failedSample'):
            data = make_capture()
            row = next(r for r in data['rows'] if r[0]=='SAMPLE' and r[1]=='Core')
            row[7] = 'true'
            with self.assertRaises(ValueError): analyze_capture(**data)
        with self.subTest('nanClock'):
            data = make_capture()
            row = next(r for r in data['rows'] if r[0]=='SAMPLE' and r[1]=='Core')
            row[4] = 'nan'
            with self.assertRaises(ValueError): analyze_capture(**data)

    def test_calibration_errors(self):
        with self.subTest('missingAfter'):
            data = make_capture()
            data['brackets'] = [b for b in data['brackets'] if b['phase']!='after']
            with self.assertRaises(ValueError): analyze_capture(**data)
        with self.subTest('sixBeforeNoAfter'):
            data = make_capture()
            for b in data['brackets']: b['phase'] = 'before'
            with self.assertRaises(ValueError): analyze_capture(**data)
        with self.subTest('inconsistentOffset'):
            data = make_capture()
            for b in data['brackets']:
                if b['key']=='Core' and b['phase']=='after':
                    b['triple'] = [120, 221, 120]
            with self.assertRaises(ValueError): analyze_capture(**data)

    def test_window_and_counter_mismatch(self):
        with self.subTest('shortWindow'):
            data = make_capture()
            for r in data['rows']:
                if r[0]=='ANCHOR' and r[1]=='Core' and r[4]=='87':
                    r[5] = '115'
            with self.assertRaises(ValueError): analyze_capture(**data)
        with self.subTest('counterMismatch'):
            data = make_capture()
            row = next(r for r in data['rows'] if r[0]=='META' and r[1]=='Core')
            row[15] = '19'
            with self.assertRaises(ValueError): analyze_capture(**data)