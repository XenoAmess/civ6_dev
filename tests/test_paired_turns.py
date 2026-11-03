from copy import deepcopy
import unittest
from paired_turn_fixture import make_pairs,records,SHA
from tools.analyze_paired_turns import analyze_pairs


class PairedTurnTests(unittest.TestCase):
    def test_all25_rows_actual_turns_and_medians(self):
        data=make_pairs();original=deepcopy(data);r=analyze_pairs(data,SHA)
        self.assertEqual(data,original);self.assertEqual(len(r['matched_rows']),25)
        self.assertEqual({x['turn'] for x in r['matched_rows']},set(range(86,91)))
        self.assertEqual((r['median_delta_ms'],r['median_ratio_percent']),(250,5))
        self.assertTrue(r['ratio_known']);self.assertTrue(r['observed_b_delta_budget_ok'])
        self.assertEqual([x['median_delta_ms'] for x in r['pair_medians']],[250]*5)

    def test_zero_control_makes_pair_and_top_ratio_unknown_without_filtering(self):
        data=make_pairs();data[0]['control']['records']=records([0,5,5,5,5]);r=analyze_pairs(data,SHA)
        self.assertIsNone(r['median_ratio_percent']);self.assertIsNone(r['pair_medians'][0]['median_ratio_percent'])
        self.assertEqual(r['pair_medians'][1]['median_ratio_percent'],5)
        self.assertFalse(r['ratio_known']);self.assertFalse(r['observed_b_delta_budget_ok'])
        self.assertEqual(len(r['matched_rows']),25);self.assertIsNone(r['matched_rows'][0]['ratio_percent'])

    def test_frozen_both_thresholds_and_negative_delta(self):
        self.assertTrue(analyze_pairs(make_pairs(5.5,5),SHA)['observed_b_delta_budget_ok'])
        self.assertFalse(analyze_pairs(make_pairs(10.75,10),SHA)['observed_b_delta_budget_ok'])
        self.assertFalse(analyze_pairs(make_pairs(2.25,2),SHA)['observed_b_delta_budget_ok'])
        result=analyze_pairs(make_pairs(4.75,5),SHA)
        self.assertEqual((result['median_delta_ms'],result['median_ratio_percent']),(-250,-5))

    def test_strict_metadata_types(self):
        for field,value in [('source_version',67.0),('source_version',True),('errors',False),('errors',0.0),('refused',False),('refused',0.0),('errors',1)]:
            data=make_pairs();data[0]['enabled'][field]=value
            with self.subTest(field=field,value=value):
                with self.assertRaises(ValueError):analyze_pairs(data,SHA)
        data=make_pairs();data[0]['pair']=True
        with self.assertRaises(ValueError):analyze_pairs(data,SHA)

    def test_missing_wrong_order_duplicate_identity_and_fixture_rejected(self):
        for change in ('missing_error','wrong_order','same_id','wrong_fixture','short_records','short_pairs'):
            data=make_pairs()
            if change=='missing_error':del data[0]['enabled']['errors']
            elif change=='wrong_order':data[1]['order'].reverse()
            elif change=='same_id':data[1]['control']['run_id']=data[0]['enabled']['run_id']
            elif change=='wrong_fixture':data[0]['control']['fixture_sha256']='2'*64
            elif change=='short_records':data[0]['control']['records'].pop()
            else:data.pop()
            with self.subTest(change=change):
                with self.assertRaises(ValueError):analyze_pairs(data,SHA)

    def test_record_metadata_times_and_cooldown(self):
        for field,value in [('pid',True),('from_turn',True),('to_turn',87),('started',False),('ended',float('nan')),('seconds',-1),('seconds',0.01),('started',1<<2048)]:
            data=make_pairs();data[0]['enabled']['records'][0][field]=value
            with self.subTest(field=field,value=type(value).__name__):
                with self.assertRaises(ValueError):analyze_pairs(data,SHA)
        data=make_pairs();row=data[0]['enabled']['records'][1];row['started']-=3;row['ended']-=3
        with self.assertRaises(ValueError):analyze_pairs(data,SHA)

    def test_derived_metric_overflow_rejected(self):
        data=make_pairs();data[0]['enabled']['records']=records([1e308,0,0,0,0])
        with self.assertRaises(ValueError):analyze_pairs(data,SHA)

    def test_input_shapes_and_sha_are_explicit(self):
        for data in (None,{},'five',b'five',bytearray(5),(x for x in make_pairs())):
            with self.subTest(type=type(data).__name__):
                with self.assertRaises(ValueError):analyze_pairs(data,SHA)
        for sha in (None,'g'*64,'A'*64,'1'*63,True):
            with self.assertRaises(ValueError):analyze_pairs(make_pairs(),sha)

    def test_global_median_uses25_individual_ratios_not_ratio_of_medians(self):
        data=make_pairs()
        for pair in data:
            pair['control']['records']=records([1,2,100,100,100])
            pair['enabled']['records']=records([2,3,101,100,99])
        r=analyze_pairs(data,SHA)
        self.assertEqual(r['median_delta_ms'],1000)
        self.assertEqual(r['median_ratio_percent'],1)
        self.assertFalse(r['observed_b_delta_budget_ok'])


if __name__=='__main__':unittest.main()
