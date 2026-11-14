"""Synthetic arithmetic inputs, never transformed Native captures."""
from copy import deepcopy
import unittest
from tests import paired_turn_fixture as fixture
from tools.analyze_paired_turns import analyze_pairs,analyze_pressure_pairs


def pressure(first=1):
    pairs=fixture.make_pairs()
    for pair in pairs:
        for variant in ('enabled','control'):
            c=pair[variant]
            c.update(source='baiqi142-pressure-paired-v1',source_version=142,initial_turn=first,
                     end_mode='ORDINARY_CALLBACK',forced=False,phase='COMPLETE',requested_turns=list(range(first,first+5)))
            for i,row in enumerate(c['records']):row.update(from_turn=first+i,to_turn=first+i+1)
    return pairs


class PressurePairedTurnTests(unittest.TestCase):
    def test_actual_labels_boundaries_and_no_mutation(self):
        for first in (0,1,2147483641):
            data=pressure(first);old=deepcopy(data);r=analyze_pressure_pairs(data,fixture.SHA,initial_turn=first)
            self.assertEqual(data,old);self.assertEqual(len(r['matched_rows']),25)
            self.assertEqual({x['turn']for x in r['matched_rows']},set(range(first+1,first+6)))
            self.assertTrue(r['observed_b_delta_budget_ok']);self.assertEqual(r['median_ratio_percent'],5)
            self.assertEqual(r['pressure_distributions']['delta_ms'],dict(p50=250,p95=250,max=250,over_500_count=0))

    def test_mode_and_calendar_metadata_types_rejected(self):
        for first in (True,1.0,-1,2147483642,None):
            with self.assertRaises(ValueError):analyze_pressure_pairs(pressure(),fixture.SHA,initial_turn=first)
        for key,value in [('source',None),('source_version',142.0),('initial_turn',True),('initial_turn',1.0),
                          ('forced',0),('phase','RECORDING'),('requested_turns',[1,2,3,4,True])]:
            data=pressure();data[0]['enabled'][key]=value
            with self.assertRaises(ValueError):analyze_pressure_pairs(data,fixture.SHA,initial_turn=1)
        for side in ('from_turn','to_turn'):
            data=pressure();data[0]['control']['records'][0][side]=85
            with self.assertRaises(ValueError):analyze_pressure_pairs(data,fixture.SHA,initial_turn=1)
        data=pressure(0);data[0]['enabled']['initial_turn']=False
        with self.assertRaises(ValueError):analyze_pressure_pairs(data,fixture.SHA,initial_turn=0)

    def test_cross_modes_and_malformed_shapes(self):
        with self.assertRaises(ValueError):analyze_pairs(pressure(85),fixture.SHA,expected_source_version=142,require_ordinary=True)
        with self.assertRaises(ValueError):analyze_pressure_pairs(fixture.make_pairs(),fixture.SHA,initial_turn=85)
        for shape in (None,{},'bad',[None]*5,[{}]*5):
            with self.assertRaises(ValueError):analyze_pressure_pairs(shape,fixture.SHA,initial_turn=1)
        legacy=analyze_pairs(fixture.make_pairs(),fixture.SHA)
        self.assertNotIn('pressure_distributions',legacy);self.assertNotIn('initial_turn',legacy)

    def test_zero_control_keeps_delta_distribution_and_unknown_whole_ratio(self):
        data=pressure();c=data[0]['control']['records'][0];c.update(ended=c['started'],seconds=0)
        r=analyze_pressure_pairs(data,fixture.SHA,initial_turn=1)
        self.assertEqual(len(r['matched_rows']),25);self.assertFalse(r['observed_b_delta_budget_ok'])
        self.assertEqual(r['pressure_distributions']['ratio_percent'],dict(p50=None,p95=None,max=None,over_10_count=None))
        self.assertEqual(r['pressure_distributions']['delta_ms']['over_500_count'],1)
        self.assertIsNone(r['pair_medians'][0]['median_ratio_percent']);self.assertEqual(r['pair_medians'][1]['median_ratio_percent'],5)

    def test_outliers_negative_rows_and_strict_descriptive_counts(self):
        data=pressure()
        for pair in data:
            c=pair['control']['records'];e=pair['enabled']['records']
            for rows,seconds in ((c,[5]*5),(e,[5.5,5.5,5.25,4.75,6])):
                for i,row in enumerate(rows):row.update(started=100+i*20,ended=100+i*20+seconds[i],seconds=seconds[i])
        r=analyze_pressure_pairs(data,fixture.SHA,initial_turn=1)
        self.assertTrue(r['observed_b_delta_budget_ok'])
        self.assertEqual(r['pressure_distributions']['delta_ms'],dict(p50=500,p95=1000,max=1000,over_500_count=5))
        self.assertEqual(r['pressure_distributions']['ratio_percent']['over_10_count'],5)
        self.assertEqual(sum(x['delta_ms']<0 for x in r['matched_rows']),5)

    def test_shared_identity_cooldown_and_overflow_gates(self):
        for change in ('run','sha','order','cooldown','overflow'):
            data=pressure()
            if change=='run':data[1]['control']['run_id']=data[0]['enabled']['run_id']
            elif change=='sha':data[0]['control']['fixture_sha256']='2'*64
            elif change=='order':data[1]['order'].reverse()
            elif change=='cooldown':data[0]['enabled']['records'][1].update(started=0,ended=5.25)
            else:data[0]['enabled']['records'][0].update(started=0,ended=1e308,seconds=1e308)
            with self.assertRaises(ValueError):analyze_pressure_pairs(data,fixture.SHA,initial_turn=1)
