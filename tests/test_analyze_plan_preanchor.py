import unittest
from test_analyze_plan_capture import capture
from tools.analyze_plan_capture import analyze_plan_capture


def v2():
    d=capture();d['source']='baiqi140-stageA-v2'
    d['pre_anchor']={'pending':0,'recorded':0,'validated':0,'errors':0}
    for row in d['samples']:row.update(preAnchor=False,argumentCount=0,allowOrders='nil')
    return d


def add_pre(d):
    d['samples'].append({'name':'Controller.RunNow','seconds':1.,'failed':False,'started':8.,'ended':9.,
        'turnStart':86,'turnEnd':86,'cityStart':10,'cityEnd':10,'anchor':10.,'windowEligible':False,
        'preAnchor':True,'argumentCount':1,'allowOrders':'false'})
    d['profile']['total_calls']+=1;d['pre_anchor'].update(recorded=1,validated=1)


class AnalyzePlanPreanchorTests(unittest.TestCase):
    def test_retained_proved_pre_native_call_is_separate_from_both_pure_ten_targets(self):
        d=v2();add_pre(d);s=analyze_plan_capture(d)
        self.assertEqual(s['samples'],201);self.assertTrue(s['overall_budget_ok'])
        self.assertEqual(s['targets']['Controller.RunNow']['pure_ten_count'],100)
        self.assertEqual(s['classification_counts']['Controller.RunNow']['before_native_anchor'],1)
        self.assertEqual(s['pre_anchor']['validated'],1)

    def test_unresolved_or_error_or_forged_proof_count_is_rejected(self):
        for edit in (lambda d:d['pre_anchor'].update(pending=1),
                     lambda d:d['pre_anchor'].update(errors=1),
                     lambda d:d['pre_anchor'].update(validated=2),
                     lambda d:d['pre_anchor'].update(recorded=True)):
            d=v2();add_pre(d);edit(d)
            with self.assertRaises(ValueError):analyze_plan_capture(d)

    def test_partial_overlap_wrong_argument_and_admin_cannot_use_pre_native_exception(self):
        for edit in (lambda r:r.update(ended=10.1,seconds=2.1),lambda r:r.update(argumentCount=0),
                     lambda r:r.update(allowOrders='true'),lambda r:r.update(name='Admin.Run'),
                     lambda r:r.update(windowEligible=True),lambda r:r.update(turnEnd=87)):
            d=v2();add_pre(d);edit(d['samples'][-1])
            with self.assertRaises(ValueError):analyze_plan_capture(d)

    def test_v1_shape_and_before_anchor_rules_are_not_retroactively_relaxed(self):
        d=capture();s=analyze_plan_capture(d)
        self.assertNotIn('pre_anchor',s)
        d['samples'][0].update(started=8.,ended=9.,seconds=1.,windowEligible=False)
        with self.assertRaises(ValueError):analyze_plan_capture(d)


if __name__=='__main__':
    unittest.main()
