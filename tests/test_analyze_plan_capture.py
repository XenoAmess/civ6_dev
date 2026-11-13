import copy
import unittest
from tools.analyze_plan_capture import analyze_plan_capture


def capture():
    d={'source':'baiqi140-stageA-v1','enabled':False,'retired':False,'subscribed':True,
       'bound':True,'qualification_errors':0,'closing_actual_turn':91,'capture_start':0.,
       'capture_stop':120.,'anchors':{str(t):10.+20*(t-86)for t in range(86,92)},
       'profile':{'capacity':4096,'aggregate_zero':False,'total_calls':200,
                  'dropped':0,'invalid_clock':0,'zero_success':0},'samples':[]}
    for name in ('Admin.Run','Controller.RunNow'):
        for t in range(86,91):
            a=d['anchors'][str(t)]
            for i in range(20):
                st=a+.02*i;en=st+.001
                d['samples'].append({'name':name,'seconds':en-st,'failed':False,
                    'started':st,'ended':en,'turnStart':t,'turnEnd':t,
                    'cityStart':10,'cityEnd':10,'anchor':a,'windowEligible':True})
    return d


class AnalyzePlanCaptureTests(unittest.TestCase):
    def test_valid_five_window_targets_have_independent_counts_and_budgets(self):
        d=capture();before=copy.deepcopy(d);s=analyze_plan_capture(d)
        self.assertEqual(d,before);self.assertTrue(s['overall_budget_ok'])
        self.assertEqual(s['targets']['Admin.Run']['pure_ten_count'],100)
        self.assertEqual(s['targets']['Controller.RunNow']['pure_ten_count'],100)
        self.assertEqual(s['eligible_calls_by_turn']['Admin.Run'],{str(t):20 for t in range(86,91)})

    def test_whole_call_tail_and_zero_samples_are_preserved(self):
        d=capture();r=d['samples'][0];r.update(started=19.99,ended=20.05,seconds=.06)
        r=d['samples'][1];r.update(ended=r['started'],seconds=0.)
        s=analyze_plan_capture(d)
        self.assertEqual(s['targets']['Admin.Run']['pure_ten_count'],100)
        self.assertEqual(s['targets']['Admin.Run']['max_ms'],60.)
        self.assertFalse(s['targets']['Admin.Run']['budget_ok'])
        self.assertTrue(s['targets']['Controller.RunNow']['budget_ok'])

    def test_nearest_rank_p95_and_each_target_minimum_are_enforced(self):
        d=capture()
        for r in d['samples'][:6]:r['seconds']=.03;r['ended']=r['started']+.03
        s=analyze_plan_capture(d)
        self.assertEqual(s['targets']['Admin.Run']['p95_ms'],30.)
        self.assertFalse(s['overall_budget_ok'])
        d=capture();d['samples'].pop();d['profile']['total_calls']-=1
        s=analyze_plan_capture(d)
        self.assertFalse(s['targets']['Controller.RunNow']['budget_ok'])
        self.assertEqual(s['targets']['Controller.RunNow']['pure_ten_count'],99)

    def test_conversion_eleven_city_and_turn_crossing_are_separate(self):
        d=capture();d['samples'][0]['cityEnd']=11
        d['samples'][1].update(cityStart=11,cityEnd=11)
        d['samples'][2]['turnEnd']=87
        s=analyze_plan_capture(d);c=s['classification_counts']['Admin.Run']
        self.assertEqual((c['10_to_11'],c['eleven_city'],c['turn_crossing'],c['pure_ten']),(1,1,1,97))
        self.assertFalse(s['overall_budget_ok'])

    def test_gate_race_is_retained_but_excluded_and_flag_must_match(self):
        d=capture();d['samples'][0].update(started=20.,ended=20.001,seconds=.001,windowEligible=False)
        s=analyze_plan_capture(d)
        self.assertEqual(s['samples'],200)
        self.assertEqual(s['classification_counts']['Admin.Run']['outside_window'],1)
        self.assertEqual(s['targets']['Admin.Run']['pure_ten_count'],99)
        d['samples'][0]['windowEligible']=True
        with self.assertRaisesRegex(ValueError,'Contradictory'):analyze_plan_capture(d)
        d=capture();d['samples'][0]['windowEligible']=False
        with self.assertRaisesRegex(ValueError,'Contradictory'):analyze_plan_capture(d)

    def test_clock_duration_forged_anchor_and_capture_bounds_are_rejected(self):
        for edit in (lambda d:d['samples'][0].update(seconds=0.),
                     lambda d:d['samples'][0].update(anchor=5.),
                     lambda d:d.update(capture_start=11.),
                     lambda d:d.update(capture_stop=109.),
                     lambda d:d['samples'][0].update(ended=121.,seconds=111.)):
            d=capture();edit(d)
            with self.assertRaises(ValueError):analyze_plan_capture(d)

    def test_missing_duplicate_shape_and_quality_counters_cannot_default_to_zero(self):
        for obj,key,value in [('profile','dropped',False),('profile','invalid_clock',1),
                              ('profile','zero_success',None),('profile','capacity',4096.),
                              ('profile','total_calls',True),('root','qualification_errors',False),
                              ('root','closing_actual_turn',91.)]:
            with self.subTest(obj=obj,key=key,value=value):
                d=capture();(d if obj=='root'else d[obj])[key]=value
                with self.assertRaises(ValueError):analyze_plan_capture(d)
        for key in ('dropped','invalid_clock','zero_success'):
            d=capture();d['profile'].pop(key)
            with self.assertRaises(ValueError):analyze_plan_capture(d)

    def test_nonfinite_bool_and_oversized_numbers_are_unknown(self):
        for value in (float('nan'),float('inf'),-float('inf'),True,10**10000):
            d=capture();d['samples'][0]['started']=value
            with self.assertRaises(ValueError):analyze_plan_capture(d)
        d=capture();d['samples'][0]['cityEnd']=True
        with self.assertRaises(ValueError):analyze_plan_capture(d)

    def test_missing_or_short_native_activity_window_is_rejected(self):
        for edit in (lambda d:d['anchors'].pop('88'),
                     lambda d:d['anchors'].update({'87':19.}),
                     lambda d:d['anchors'].update({'91':90.})):
            d=capture();edit(d)
            with self.assertRaises(ValueError):analyze_plan_capture(d)

    def test_failed_wrong_target_lifecycle_and_counter_mismatch_reject(self):
        for edit in (lambda d:d['samples'][0].update(failed=True),
                     lambda d:d['samples'][0].update(name='Tick'),
                     lambda d:d.update(enabled=True),
                     lambda d:d.update(retired=True),
                     lambda d:d.update(subscribed=False),
                     lambda d:d['profile'].update(total_calls=201)):
            d=capture();edit(d)
            with self.assertRaises(ValueError):analyze_plan_capture(d)

    def test_finite_seconds_cannot_overflow_reported_milliseconds(self):
        d=capture();d['capture_stop']=1e308
        d['samples'][0].update(ended=1e308,seconds=1e308)
        with self.assertRaisesRegex(ValueError,'millisecond'):analyze_plan_capture(d)


if __name__=='__main__':
    unittest.main()
