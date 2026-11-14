"""One fallback proposal per callback without abandoning unseen alternatives."""
from pathlib import Path
import unittest
import test_baiqi_settler_direct_goal as fixture

ROOT=Path(__file__).resolve().parents[1]


class OneSettlementValidationTests(unittest.TestCase):
    candidate_source=None

    def setUp(self):
        source=self.candidate_source
        if source is None:source=(ROOT/'mod/Baiqi/Lua/BaiqiController.lua').read_text(encoding='utf-8')
        self.case=fixture.DirectSettlerGoalTests()
        self.case.candidate_source=source+'\nTestEnumerateSites=SettlementSites\n'
        self.case.setUp();self.lua,self.w,self.c=self.case.lua,self.case.w,self.case.c
        self.lua.execute('''
TestWorld.goalProposals['2']=nil
BaiqiSettlementWarning.Read=function(_,_,index)
 if index==46 then return'KNOWN_NEGATIVE'end;return'NOT_APPLICABLE'
end
''')

    def count(self,index):return self.w.supportReads[index]or 0

    def test_rejected_first_site_yields_without_skip_then_moves_to_fresh_alternative(self):
        self.case.step()
        self.assertEqual((self.count(46),self.count(47)),(1,0))
        self.assertEqual(len(self.w.unitRequests),0)
        self.assertEqual(self.w.hintReads,1)
        self.case.step()
        self.assertEqual((self.count(46),self.count(47)),(1,1))
        self.assertEqual(self.case.moves(),[(2,2,4)])
        self.assertEqual(self.w.hintReads,2)

    def test_exhaustion_waits_only_after_each_rejected_site_has_its_own_callback(self):
        self.lua.execute("BaiqiSettlementWarning.Read=function()return'KNOWN_NEGATIVE'end")
        self.case.step()
        self.assertEqual((self.count(46),self.count(47)),(1,0))
        self.assertEqual(len(self.w.unitRequests),0)
        self.case.step()
        self.assertEqual((self.count(46),self.count(47)),(1,1))
        self.assertEqual(self.case.moves(),[])
        self.assertEqual(len(self.w.unitRequests),1)
        self.assertEqual((self.w.unitRequests[1].unit,self.w.unitRequests[1].op),(2,17))
        self.case.step()
        self.assertEqual((self.count(46),self.count(47)),(1,1))

    def test_default_keeps_full_enumeration_and_optin_records_attempted_id(self):
        self.case.step()  # Initialize actual player/visibility context.
        self.lua.execute('''
TestWorld.supportReads={}
local results,more=TestEnumerateSites(TestWorld.objects.player,{},true,nil,2,nil)
assert(#results==1 and results[1].index==47 and more==false)
assert(TestWorld.supportReads[46]==1 and TestWorld.supportReads[47]==1)
local excluded={[46]=true}
results,more=TestEnumerateSites(TestWorld.objects.player,{},true,excluded,2,nil,true)
assert(#results==1 and results[1].index==47 and more==false and excluded[47]==true)
''')

    def test_bad_optin_rejected_before_native_query(self):
        self.lua.execute('''
local player=TestWorld.objects.player;local original=player.GetGrandStrategicAI
TestWorld.aiReads=0
player.GetGrandStrategicAI=function(self)TestWorld.aiReads=TestWorld.aiReads+1;return original(self)end
for _,mode in ipairs({1,'true',{},function()end})do
 assert(not pcall(TestEnumerateSites,player,{},true,{},2,nil,mode))
end
assert(not pcall(TestEnumerateSites,player,{},false,{},2,nil,true))
assert(not pcall(TestEnumerateSites,player,{},true,nil,2,nil,true))
assert(TestWorld.aiReads==0)
''')
        self.assertEqual(len(self.w.unitRequests),0)


if __name__=='__main__':unittest.main()
