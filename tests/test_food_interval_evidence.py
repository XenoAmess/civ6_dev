"""Independent evidence stays unknown when a neighboring domain cannot qualify."""
import copy
import json
import unittest
from tools.food_interval_evidence import analyze_food_interval


class FoodIntervalEvidenceTests(unittest.TestCase):
    def setUp(self):
        self.u = dict(scope_key='one-instance-city', cityID=458758, turn=272, population=11,
                      stock=1.34765625, surplus=1, project_hash=-1205325871, project_progress=63)
        self.v = dict(self.u, turn=273, stock=.34765625, surplus=-1, project_progress=100)
        self.c = {k: self.u[k] for k in ('scope_key', 'cityID', 'turn', 'surplus')}
        self.d = {k: self.v[k] for k in ('scope_key', 'cityID', 'turn', 'surplus')}
        self.e = dict(scope_key=self.u['scope_key'], cityID=458758, turn=273,
                      event='CityProductionCompleted', productionKind=3, productionIndex=10)

    def read(self, events=None):
        return analyze_food_interval(self.u, self.v, self.c, self.d, events)

    def test_qualified_delta_survives_missing_core_or_event_coverage(self):
        result = analyze_food_interval(self.u, self.v, None, None, None)
        self.assertEqual(result['ui_interval']['stock_delta'], -1)
        self.assertFalse(result['core_comparison']['qualified'])
        self.assertFalse(result['production']['qualified'])
        self.assertIsNone(result['causal_conclusion'])

    def test_scope_city_turn_or_population_mismatch_never_qualifies_ui_delta(self):
        for key, value in [('scope_key', 'foreign'), ('cityID', 99), ('turn', 272), ('population', 10)]:
            with self.subTest(key=key):
                result = analyze_food_interval(self.u, dict(self.v, **{key: value}), self.c, self.d, [self.e])
                self.assertFalse(result['ui_interval']['qualified'])
                self.assertIsNone(result['ui_interval']['stock_delta'])
                self.assertFalse(result['production']['qualified'])
                self.assertEqual(result['production']['events'], [])

    def test_core_each_endpoint_must_match_corresponding_ui(self):
        for key, value in [('scope_key', 'foreign'), ('cityID', 99), ('turn', 271), ('surplus', True)]:
            with self.subTest(key=key):
                result = analyze_food_interval(self.u, self.v, dict(self.c, **{key: value}), self.d, [])
                self.assertFalse(result['core_comparison']['qualified'])
                self.assertEqual(result['ui_interval']['stock_delta'], -1)
        self.d['surplus'] = 4
        result = self.read()
        self.assertTrue(result['core_comparison']['after_conflict'])
        self.assertEqual(result['core_comparison']['reason'], 'ALIGNED_ENDPOINT_VALUES_NOT_ATOMIC_SAMPLES')

    def test_missing_empty_and_overflow_events_have_distinct_coverage(self):
        self.assertFalse(self.read(None)['production']['qualified'])
        empty = self.read([])['production']
        self.assertTrue(empty['qualified'])
        self.assertEqual(empty['reason'], 'BOUNDED_RECORDED_LIST_ONLY')
        overflow = self.read([self.e] * 129)['production']
        self.assertFalse(overflow['qualified'])
        self.assertEqual(overflow['events'], [])

    def test_only_aligned_completed_events_are_retained_without_claiming_causality(self):
        events = [dict(self.e, scope_key='foreign'), dict(self.e, cityID=99),
                  dict(self.e, turn=274), dict(self.e, event='CityProductionUpdated'), self.e]
        result = self.read(events)
        self.assertTrue(result['production']['qualified'])
        self.assertEqual(result['production']['events'], [self.e])
        self.assertIsNone(result['causal_conclusion'])

    def test_bad_nested_types_and_malformed_events_do_not_hide_coverage_gaps(self):
        for event in (None, [], dict(self.e, event='UnitAdded'), dict(self.e, productionIndex=True),
                      dict(self.e, cityID={}), dict(self.e, productionKind=[])):
            with self.subTest(event=event):
                result = self.read([self.e, event])
                self.assertFalse(result['production']['qualified'])
                self.assertEqual(result['production']['events'], [self.e])

    def test_huge_integers_booleans_nonfinite_and_bad_fields_do_not_throw(self):
        for value in (10**10000, True, float('nan'), float('inf'), {}, [], None):
            for key in ('stock', 'project_hash', 'project_progress'):
                with self.subTest(type=type(value).__name__, key=key):
                    result = analyze_food_interval(dict(self.u, **{key: value}), self.v, self.c, self.d, [])
                    self.assertFalse(result['ui_interval']['qualified'])
                    json.dumps(result, allow_nan=False)

    def test_output_sanitizes_event_extras_and_never_mutates_inputs(self):
        extra = dict(self.e, untyped_extra={'nested': object()})
        original = copy.deepcopy([self.u, self.v, self.c, self.d, self.e])
        result = self.read([extra])
        json.dumps(result, allow_nan=False)
        self.assertEqual(result['production']['events'], [self.e])
        self.assertEqual(original, [self.u, self.v, self.c, self.d, self.e])
        result['production']['events'][0]['turn'] = 999
        self.assertEqual(extra['turn'], 273)

    def test_core_endpoint_values_remain_independent_of_invalid_ui_stock(self):
        result = analyze_food_interval(dict(self.u, stock=None), self.v, self.c, self.d, [])
        self.assertFalse(result['ui_interval']['qualified'])
        self.assertTrue(result['core_comparison']['qualified'])
        self.assertFalse(result['core_comparison']['before_conflict'])


if __name__ == '__main__':
    unittest.main()
