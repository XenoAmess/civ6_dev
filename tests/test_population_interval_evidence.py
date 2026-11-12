import copy
import json
import unittest
from tools.population_interval_evidence import analyze_population_interval


class PopulationIntervalTests(unittest.TestCase):
    def setUp(self):
        c=dict(cityID=655369,owner=0,x=59,y=28,population=15)
        self.before=dict(scope_key='owned',turn=293,complete=True,cities=[c])
        self.after=dict(scope_key='owned',turn=294,complete=True,cities=[dict(c,population=14)])

    def result(self): return analyze_population_interval(self.before,self.after)

    def test_loss_is_qualified_evidence_but_never_no_loss_or_end_permission(self):
        r=self.result();self.assertTrue(r['qualified']);self.assertEqual(r['status'],'POPULATION_LOSS')
        self.assertEqual(r['losses'],[dict(cityID=655369,x=59,y=28,before_population=15,after_population=14,delta=-1)])
        self.assertIsNone(r['causal_conclusion']);self.assertNotIn('EndPermission',r)
        json.dumps(r)

    def test_same_or_increased_population_has_no_loss(self):
        for population in (15,16):
            self.after['cities'][0]['population']=population
            self.assertEqual(self.result()['status'],'NO_LOSS')

    def test_new_cities_separate_and_losses_sorted(self):
        self.before['cities'].append(dict(cityID=1,owner=0,x=1,y=2,population=3))
        self.after['cities'] += [dict(cityID=1,owner=0,x=1,y=2,population=2),dict(cityID=900,owner=0,x=9,y=2,population=1)]
        r=self.result();self.assertEqual([v['cityID']for v in r['losses']],[1,655369]);self.assertEqual(r['new_city_ids'],[900])

    def test_missing_or_duplicate_or_shifted_city_is_unknown(self):
        variants=[[],[self.after['cities'][0],self.after['cities'][0]],
                  [dict(self.after['cities'][0],cityID=42)],[dict(self.after['cities'][0],x=60)]]
        for cities in variants:
            a=dict(self.after,cities=cities)
            self.assertEqual(analyze_population_interval(self.before,a)['status'],'UNKNOWN')

    def test_snapshot_scope_turn_complete_and_container_must_qualify(self):
        for field,values in {'scope_key':['other','',None,0],'turn':[293,295,True,294.0,-1,100001,10**10000],
                             'complete':[False,1,None],'cities':[None,{},[],[None]]}.items():
            for value in values:
                a=dict(self.after,**{field:value})
                self.assertEqual(analyze_population_interval(self.before,a)['status'],'UNKNOWN',field)
        for value in (None,[],0,False,'bad'):
            self.assertEqual(analyze_population_interval(value,self.after)['status'],'UNKNOWN')
            self.assertEqual(analyze_population_interval(self.before,value)['status'],'UNKNOWN')

    def test_every_city_field_required_and_strict(self):
        for side in ('before','after'):
            for field in ('cityID','owner','x','y','population'):
                for value in (None,True,1.0,'1',float('inf'),float('nan'),-1):
                    b,a=copy.deepcopy((self.before,self.after));target=b if side=='before'else a
                    target['cities'][0][field]=value
                    self.assertEqual(analyze_population_interval(b,a)['status'],'UNKNOWN',field)
                b,a=copy.deepcopy((self.before,self.after));target=b if side=='before'else a
                del target['cities'][0][field]
                self.assertEqual(analyze_population_interval(b,a)['status'],'UNKNOWN')

    def test_eight_huge_integer_positions_do_not_throw(self):
        for side in ('before','after'):
            for field in ('cityID','x','y','population'):
                b,a=copy.deepcopy((self.before,self.after));target=b if side=='before'else a
                target['cities'][0][field]=10**10000
                self.assertEqual(analyze_population_interval(b,a)['status'],'UNKNOWN')

    def test_whole_collection_not_valid_prefix(self):
        for side in ('before','after'):
            b,a=copy.deepcopy((self.before,self.after));target=b if side=='before'else a
            target['cities'].append(dict(cityID=42,owner=1,x=1,y=1,population=1))
            self.assertEqual(analyze_population_interval(b,a)['status'],'UNKNOWN')
        cities=[dict(cityID=i,owner=0,x=1,y=1,population=1)for i in range(257)]
        self.assertEqual(analyze_population_interval(dict(self.before,cities=cities),self.after)['status'],'UNKNOWN')

    def test_unknown_outputs_are_empty_and_have_no_cause(self):
        r=analyze_population_interval(None,self.after)
        self.assertFalse(r['qualified']);self.assertEqual(r['losses'],[])
        self.assertEqual(r['new_city_ids'],[]);self.assertIsNone(r['causal_conclusion'])

    def test_inputs_unchanged_and_extras_not_returned_or_aliased(self):
        self.before['cities'][0]['extra']={'data':[1,2]}
        before=copy.deepcopy((self.before,self.after));r=self.result()
        self.assertEqual((self.before,self.after),before)
        self.assertNotIn('extra',r['losses'][0])
        r['losses'][0]['x']=0;self.assertEqual(self.before['cities'][0]['x'],59)


if __name__=='__main__':unittest.main()
