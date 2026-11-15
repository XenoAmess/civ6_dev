"""Reject unavailable districts before costly placement without retaining authority."""
import unittest
from tests import test_baiqi_district_improvements as districts


class DistrictScanGateTests(unittest.TestCase):
    def setUp(self):
        self.case=districts.DistrictImprovementTests(methodName='runTest');self.case.setUp()
        self.lua,self.w,self.c=self.case.lua,self.case.w,self.case.c
        self.lua.execute('''local w=TestWorld;w.firstAllowed=true;w.secondAllowed=true
w.placementReads=0;w.secondReads=0;w.placedReads=0
local p=w.plot;local place=p.CanHaveDistrict
p.CanHaveDistrict=function(...)
 w.placementReads=w.placementReads+1
 if w.placementShock then w.placementShock()end
 return place(...)
end
local q=w.objects.city:GetBuildQueue();local placed=q.HasBeenPlaced
q.HasBeenPlaced=function(...)w.placedReads=w.placedReads+1;return placed(...)end
q.CanProduce=function(self,hash,mode,check)
 if hash~=777 then return false end
 if mode==true then return w.firstAllowed end
 assert(mode==false and check==true);w.secondReads=w.secondReads+1
 if w.finalReject and w.eligibilityChecks==1 then return false end
 return w.secondAllowed
end''')

    def test_false_unknown_and_untyped_second_mode_skip_all_placement_work(self):
        for value in (False,None,0,'true'):
            with self.subTest(value=value):
                self.setUp();self.w.secondAllowed=value;self.c.RunNow()
                self.assertEqual((self.w.placementReads,self.w.placedReads,self.w.eligibilityChecks),(0,0,0))
                self.assertEqual(len(self.w.cityRequests),0)

    def test_first_mode_rejection_does_not_query_second_mode_or_placements(self):
        self.w.firstAllowed=False;self.c.RunNow()
        self.assertEqual((self.w.secondReads,self.w.placementReads,self.w.placedReads),(0,0,0))
        self.assertEqual(len(self.w.cityRequests),0)

    def test_both_modes_still_allow_the_same_choice_and_final_native_checks(self):
        self.case.run_city(1)
        self.assertEqual(self.w.eligibilityChecks,2)
        self.assertGreaterEqual(self.w.secondReads,2)
        self.assertGreaterEqual(self.w.placementReads,2)

    def test_positive_preflight_does_not_cover_a_change_during_placement(self):
        self.lua.execute('TestWorld.placementShock=function()TestWorld.secondAllowed=false end')
        self.case.run_city(0)
        self.assertGreater(self.w.placementReads,0)
        self.assertEqual(self.w.eligibilityChecks,0)

    def test_final_second_mode_rejection_still_blocks_the_actual_writer(self):
        self.w.finalReject=True;self.case.run_city(0)
        self.assertEqual(self.w.eligibilityChecks,1)


if __name__=='__main__':unittest.main()
