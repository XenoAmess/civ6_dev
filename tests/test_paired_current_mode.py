import copy
import unittest
from paired_turn_fixture import make_pairs,SHA
from tools.analyze_paired_turns import analyze_pairs,validate_capture_mode


def current_pairs():
    pairs=make_pairs()
    for p in pairs:
        for v in ('enabled','control'):
            p[v].update(source_version=140,end_mode='ORDINARY_CALLBACK',forced=False,
                        phase='COMPLETE',requested_turns=list(range(85,90)))
    return pairs


class PairedCurrentModeTests(unittest.TestCase):
    def test_actual25_segment_arithmetic_and_current_source_are_reported_without_mutation(self):
        p=current_pairs();before=copy.deepcopy(p)
        s=analyze_pairs(p,SHA,expected_source_version=140,require_ordinary=True)
        self.assertEqual(p,before);self.assertEqual(len(s['matched_rows']),25)
        self.assertEqual(s['source_version'],140);self.assertTrue(s['ordinary_required'])
        self.assertEqual(s['median_delta_ms'],250);self.assertEqual(s['median_ratio_percent'],5)

    def test_forced_unknown_mode_missing_phase_or_non_integer_turns_are_rejected(self):
        for edit in (lambda c:c.update(forced=True),lambda c:c.update(forced=0),
                     lambda c:c.update(end_mode='LEGACY_USER_FORCED'),lambda c:c.pop('phase'),
                     lambda c:c.update(requested_turns=[85.,86,87,88,89]),
                     lambda c:c.update(requested_turns=[85,86,87,88,89,90])):
            p=current_pairs();edit(p[0]['enabled'])
            with self.assertRaises(ValueError):analyze_pairs(p,SHA,expected_source_version=140,require_ordinary=True)

    def test_mixed_source_or_invalid_option_cannot_be_accepted(self):
        p=current_pairs();p[2]['control']['source_version']=67
        with self.assertRaises(ValueError):analyze_pairs(p,SHA,expected_source_version=140,require_ordinary=True)
        for version,ordinary in ((True,False),(143,False),(67,True),(140,1)):
            with self.assertRaises(ValueError):validate_capture_mode({},version,ordinary)

    def test_legacy67_shape_remains_and140_requires_an_explicit_source_choice(self):
        s=analyze_pairs(make_pairs(),SHA)
        self.assertNotIn('source_version',s);self.assertNotIn('ordinary_required',s)
        with self.assertRaises(ValueError):analyze_pairs(current_pairs(),SHA)

    def test_zero_control_and_frozen_limits_are_not_relaxed_for_current_mode(self):
        p=current_pairs()
        for r in p[0]['control']['records']:r.update(ended=r['started'],seconds=0)
        s=analyze_pairs(p,SHA,expected_source_version=140,require_ordinary=True)
        self.assertIsNone(s['median_ratio_percent']);self.assertFalse(s['observed_b_delta_budget_ok'])
        p=current_pairs()
        for pair in p:
            for r in pair['enabled']['records']:r.update(ended=r['started']+6,seconds=6)
        s=analyze_pairs(p,SHA,expected_source_version=140,require_ordinary=True)
        self.assertFalse(s['observed_b_delta_budget_ok'])


if __name__=='__main__':
    unittest.main()
