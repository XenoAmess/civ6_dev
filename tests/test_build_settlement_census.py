from pathlib import Path
import unittest
from unittest.mock import patch
from tools.build_settlement_census_mod import transform,restore_release,EDITS
from tools.analyze_settlement_census import classify_settlement_call
import test_baiqi_settler_site_budget as slicing
import test_baiqi_settlement_queries as recruitment

ROOT=Path(__file__).resolve().parents[1]
CONTROLLER=ROOT/'mod/Baiqi/Lua/BaiqiController.lua'


class SettlementCensusTransformTests(unittest.TestCase):
    def setUp(self):
        self.raw=CONTROLLER.read_text(encoding='utf-8')
        self.text,self.prefix=transform(self.raw)

    def test_exact_anchors_and_inverse_fail_closed(self):
        self.assertEqual(restore_release(self.text,self.prefix),self.raw)
        old=EDITS[0][0]
        for raw in (self.raw.replace(old,'changed',1),self.raw+'\n'+old):
            with self.assertRaises(ValueError):transform(raw)
        with self.assertRaises(ValueError):restore_release(self.text+'\n'+EDITS[-1][1],self.prefix)

    def settler_case(self,source):
        case=slicing.OneSettlementValidationTests();case.candidate_source=source;case.setUp()
        case.lua.execute('qaClock=0;Automation={GetTime=function()qaClock=qaClock+.001;return qaClock end}')
        return case

    def test_real_sliced_search_has_unvisited_then_accepted_without_extra_reads(self):
        baseline=self.settler_case(self.raw);observed=self.settler_case(self.text)
        for step in range(2):
            baseline.case.step();observed.case.step()
            self.assertEqual(baseline.case.moves(),observed.case.moves())
            self.assertEqual(baseline.w.hintReads,observed.w.hintReads)
            for index in (46,47):self.assertEqual(baseline.count(index),observed.count(index))
            self.assertEqual(len(baseline.w.unitRequests),len(observed.w.unitRequests))
        rows=observed.lua.globals().P6SettlementCensus.Snapshot().rows
        self.assertEqual(len(rows),2)
        first=classify_settlement_call(dict(rows[1].items()));second=classify_settlement_call(dict(rows[2].items()))
        self.assertEqual((first['outcome'],first['unvisited']),('PARTIAL_UNVISITED',1))
        self.assertEqual(second['outcome'],'HAS_ACCEPTED_SITE')
        self.assertIsNone(first['global_no_legal_site'])

    def test_existing_slicing_safety_and_return_contracts_on_observer(self):
        names=unittest.defaultTestLoader.getTestCaseNames(slicing.OneSettlementValidationTests)
        for name in names:
            with self.subTest(name=name):
                case=self.settler_case(self.text);getattr(case,name)()

    def test_real_recruitment_choice_and_fresh_write_keep_all_existing_guards(self):
        old_read=Path.read_text
        def read(path,*args,**kwargs):
            if path.resolve()==CONTROLLER.resolve():return self.text
            return old_read(path,*args,**kwargs)
        for name in unittest.defaultTestLoader.getTestCaseNames(recruitment.SettlementQueryTests):
            with self.subTest(name=name),patch.object(Path,'read_text',read):
                case=recruitment.SettlementQueryTests(name);case.setUp()
                case.lua.execute('qaClock=0;Automation={GetTime=function()qaClock=qaClock+.001;return qaClock end}')
                getattr(case,name)()
                rows=case.lua.globals().P6SettlementCensus.Snapshot().rows
                for r in rows.values():
                    classified=classify_settlement_call(dict(r.items()))
                    self.assertIn(classified['caller'],('recruit_choice','recruit_write'))
                if name=='test_actual_settler_dispatch_queries_initial_and_fresh_sites_then_reserves_budget':
                    self.assertEqual([r.caller for r in rows.values()],['recruit_choice','recruit_write'])


if __name__=='__main__':unittest.main()
