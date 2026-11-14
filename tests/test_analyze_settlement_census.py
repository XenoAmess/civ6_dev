import copy
import unittest
from tools.analyze_settlement_census import classify_settlement_call


def row(**updates):
    d=dict(caller='settler_alternatives',first_only=True,one_validation=True,
           preferred_supplied=False,excluded_supplied=True,ai_available=True,
           hints_kind='table',raw_hints=2,admitted=2,visited=1,cheap_pass=1,
           support_true=0,support_false=1,support_unknown=0,returned=0,
           exhausted=False,failed=False,started=1.,ended=2.,
           turn_start=334,turn_end=334,cities_start=11,cities_end=11)
    d.update(updates);return d


class SettlementCensusAnalysisTests(unittest.TestCase):
    def test_unvisited_candidate_prevents_exhaustion_claim(self):
        d=row();before=copy.deepcopy(d);s=classify_settlement_call(d)
        self.assertEqual(d,before)
        self.assertEqual(s,dict(caller='settler_alternatives',outcome='PARTIAL_UNVISITED',
            many_candidate_pool=False,global_no_legal_site=None,visited=1,unvisited=1))

    def test_exhausted_pool_is_scoped_even_with_exclusions(self):
        s=classify_settlement_call(row(admitted=1,raw_hints=12,exhausted=True))
        self.assertEqual(s['outcome'],'EXHAUSTED_NO_ACCEPTED_SITE_IN_POOL')
        self.assertIsNone(s['global_no_legal_site'])
        self.assertFalse(s['many_candidate_pool'])

    def test_empty_table_nil_and_unavailable_ai_are_distinct(self):
        d=row(raw_hints=0,admitted=0,visited=0,cheap_pass=0,support_false=0,exhausted=True)
        self.assertEqual(classify_settlement_call(d)['outcome'],'EMPTY_OBSERVED_POOL')
        for hints,ai in (('nil',True),('boolean',True),('NOT_CALLED',False)):
            self.assertEqual(classify_settlement_call({**d,'hints_kind':hints,'ai_available':ai})['outcome'],'UNKNOWN')

    def test_unknown_and_known_positive_have_explicit_precedence(self):
        self.assertEqual(classify_settlement_call(row(support_false=0,support_unknown=1))['outcome'],'UNKNOWN')
        d=row(one_validation=False,first_only=False,visited=2,cheap_pass=2,support_false=0,
              support_unknown=1,support_true=1,returned=1,exhausted=True)
        self.assertEqual(classify_settlement_call(d)['outcome'],'HAS_ACCEPTED_SITE')

    def test_many_means_actual_pool_threshold_independent_of_early_return(self):
        for n in (11,12,20):
            s=classify_settlement_call(row(raw_hints=n,admitted=n,support_false=0,support_true=1,returned=1))
            self.assertEqual(s['many_candidate_pool'],n>=12)
            self.assertEqual(s['outcome'],'HAS_ACCEPTED_SITE')

    def test_schema_metadata_types_and_nonfinite_clocks_are_rejected(self):
        d=row()
        for k in d:
            bad=d.copy();bad.pop(k)
            with self.subTest(missing=k),self.assertRaises(ValueError):classify_settlement_call(bad)
        for updates in ({'extra':0},{'failed':True},{'failed':0},{'caller':[]},
                        {'visited':True},{'turn_start':False},{'cities_start':-1},
                        {'raw_hints':2147483648},{'started':float('nan')},
                        {'ended':float('inf')},{'started':10**10000},{'ended':True},
                        {'started':-10**308,'ended':10**308},
                        {'ended':0.},{'turn_end':333}):
            with self.subTest(keys=tuple(updates)),self.assertRaises(ValueError):classify_settlement_call(row(**updates))

    def test_inconsistent_denominators_and_modes_are_rejected(self):
        for updates in ({'raw_hints':0},{'visited':3},{'cheap_pass':2},
                        {'support_false':0},{'returned':1},{'exhausted':True},
                        {'one_validation':True,'first_only':False},
                        {'excluded_supplied':False},{'hints_kind':'NOT_CALLED'},
                        {'hints_kind':'nil'},{'ai_available':False}):
            with self.subTest(updates=updates),self.assertRaises(ValueError):classify_settlement_call(row(**updates))


if __name__=='__main__':unittest.main()
