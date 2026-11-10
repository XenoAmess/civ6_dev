import unittest, uuid, xml.etree.ElementTree as ET
from pathlib import Path
from observed_capture_fixture import make_capture, make_bounded_capture
from observed_driver_harness import DriverHarness
from tools.analyze_observed_capture import analyze_capture
from tools.run_observed_acceptance import run
from tools.diagnostic_quotas import bounded_quotas

class TestBoundedObservation(unittest.TestCase):
    def test_bounded_vs_raw_equivalence(self):
        raw=make_capture(); bounded=make_bounded_capture()
        r=analyze_capture(raw['rows'],raw['brackets'],raw['expected_keys'],raw['capture_bounds'],sample_budget=None)
        b=analyze_capture(bounded['rows'],bounded['brackets'],bounded['expected_keys'],bounded['capture_bounds'],sample_budget=2)
        self.assertEqual(len(r['windows']),5)
        for rw,bw in zip(r['windows'],b['windows']):
            self.assertEqual(rw['turn'],bw['turn'])
            self.assertEqual(rw['observed_union_ms'],bw['observed_union_ms'])
            self.assertEqual(rw['clipped_inclusive_sum_ms_not_cpu'],bw['clipped_inclusive_sum_ms_not_cpu'])
        self.assertEqual(b['samples'],2)
        self.assertAlmostEqual(b['windows'][0]['observed_union_ms'],3,delta=1e-8)
        self.assertEqual(b['aggregate_zero_success_calls'],1)
        self.assertEqual(b['configured_retained_sample_budget'],2)
        self.assertEqual(sum(t['calls'] for t in b['complete_turn_writes']),70)

    def test_missing_zero_fails(self):
        d=make_bounded_capture(); d['rows']=[r for r in d['rows'] if r[0]!='ZERO']
        with self.assertRaises(ValueError): analyze_capture(d['rows'],d['brackets'],d['expected_keys'],d['capture_bounds'],sample_budget=2)

    def test_duplicate_or_invalid_zero_fails(self):
        d=make_bounded_capture(); d['rows'].append(['ZERO','Core','0','1'])
        with self.assertRaises(ValueError): analyze_capture(d['rows'],d['brackets'],d['expected_keys'],d['capture_bounds'],sample_budget=2)
        d2=make_bounded_capture(); d2['rows']=[r if r[0]!='ZERO' or r[1]!='Core' else ['ZERO','Core','-1','1'] for r in d2['rows']]
        with self.assertRaises(ValueError): analyze_capture(d2['rows'],d2['brackets'],d2['expected_keys'],d2['capture_bounds'],sample_budget=2)

        d3=make_bounded_capture()
        next(row for row in d3['rows'] if row[0]=='ZERO' and row[1]=='UI')[2]='0'
        with self.assertRaises(ValueError):analyze_capture(**d3)

    def test_global_budget_validation(self):
        d=make_bounded_capture()
        with self.assertRaises(ValueError): analyze_capture(d['rows'],d['brackets'],d['expected_keys'],d['capture_bounds'],sample_budget=1)
        with self.assertRaises(ValueError): analyze_capture(d['rows'],d['brackets'],d['expected_keys'],d['capture_bounds'],sample_budget=False)

    def test_per_context_over_cap(self):
        d=make_capture()
        d['rows']+=['ZERO','Core','0','1'],['ZERO','UI','0','1']
        with self.assertRaises(ValueError): analyze_capture(d['rows'],d['brackets'],d['expected_keys'],d['capture_bounds'],sample_budget=2)

    def test_schema_mismatch(self):
        d=make_capture()
        with self.assertRaises(ValueError): analyze_capture(d['rows'],d['brackets'],d['expected_keys'],d['capture_bounds'],sample_budget=2)
        d2=make_bounded_capture()
        with self.assertRaises(ValueError): analyze_capture(d2['rows'],d2['brackets'],d2['expected_keys'],d2['capture_bounds'],sample_budget=None)

    def test_manifest_quotas(self):
        info=ET.fromstring((Path(__file__).parents[1]/'mod/Baiqi/Baiqi.modinfo').read_bytes())
        keys=[e.findtext('Properties/LuaReplace') for e in info.findall('InGameActions/ReplaceUIScript')]
        keys+=['UI/BaiqiExecutor.lua','Lua/BaiqiGameplay.lua']
        original=list(keys);q=bounded_quotas(keys)
        self.assertEqual(keys,original);self.assertEqual(list(q),keys)
        with self.assertRaises(TypeError):bounded_quotas((x for x in keys))
        from collections import UserDict
        with self.assertRaises(TypeError):bounded_quotas(UserDict.fromkeys(keys))
        bad=list(keys);bad[bad.index('UI/BaiqiExecutor.lua')]='UI/MissingOverride.lua'
        with self.assertRaises(ValueError):bounded_quotas(bad)
        self.assertEqual(len(q),33); self.assertEqual(sum(q.values()),4096)
        self.assertEqual(q['UI/BaiqiWorldCrisisPopup.lua'],16)
        self.assertEqual(q['UI/BaiqiExecutor.lua'],2032)
        legacy=[k for k in keys if k!='UI/BaiqiWorldCrisisPopup.lua']
        old=bounded_quotas(legacy)
        self.assertEqual(len(old),32);self.assertEqual(sum(old.values()),4096)
        self.assertEqual(old['UI/BaiqiExecutor.lua'],2048)
        unknown=[k if k!='UI/BaiqiWorldCrisisPopup.lua' else 'UI/Unknown.lua' for k in keys]
        with self.assertRaises(ValueError):bounded_quotas(unknown)
        self.assertTrue(all(isinstance(v,int) and v>0 for v in q.values()))
        with self.assertRaises(ValueError): bounded_quotas(keys[:-1])
        with self.assertRaises(ValueError): bounded_quotas(keys+keys[:1])

    def test_driver_budget_abort(self):
        h=DriverHarness()
        h.lua.execute("for _,e in pairs(ExposedMembers.P6BaiqiOwnRegistry.entries) do e.Snapshot().profile.capacity=129 end")
        ledger=Path('.local-model/bounded-observation-tests')/uuid.uuid4().hex
        with self.assertRaises(Exception):
            run(h.query,h.diplomacy_visible,h.now,h.sleep,h.emit,ledger,sample_budget=4096)
        self.assertEqual(h.actions,[])
        self.assertTrue(h.all_recording(False))
        h2=DriverHarness();ledger2=Path('.local-model/bounded-observation-tests')/uuid.uuid4().hex
        result=run(h2.query,h2.diplomacy_visible,h2.now,h2.sleep,h2.emit,ledger2,sample_budget=4096)
        self.assertEqual(result['requested_turns'],[85,86,87,88,89,90])
        self.assertTrue(h2.all_recording(False))
