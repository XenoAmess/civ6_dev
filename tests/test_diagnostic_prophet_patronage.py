"""Read-only Prophet quotes never confer recruitment or payment authority."""
from pathlib import Path
import os
import unittest
from lupa.lua51 import LuaRuntime

ROOT = Path(__file__).resolve().parents[1]
FIXTURE = r'''
W={turn=180,gold=500,faith=300,goldCost=1200,faithCost=800,
 canRecruit=false,canGold=false,canFaith=false,quoteReads=0,writes=0,
 timeline={{Class=0,Individual=0}}}
local w=W
local gp={}
function gp:GetTimeline()if w.throw then error('native unavailable')end;return w.timeline end
function gp:CanRecruitPerson(pid,id)
 assert(self==gp and pid==0 and id==0);w.quoteReads=w.quoteReads+1;return w.canRecruit
end
function gp:CanPatronizePerson(pid,id,yield)
 assert(self==gp and pid==0 and id==0 and(yield==0 or yield==5))
 w.quoteReads=w.quoteReads+1;if yield==0 then return w.canGold end;return w.canFaith
end
function gp:GetPatronizeCost(pid,id,yield)
 assert(self==gp and pid==0 and id==0 and(yield==0 or yield==5))
 w.quoteReads=w.quoteReads+1;if yield==0 then return w.goldCost end;return w.faithCost
end
local function write()w.writes=w.writes+1;error('forbidden write')end
local cfg={IsHuman=function()return not w.nonhuman end,
 GetLeaderTypeName=function()return w.leader or 'LEADER_BAIQI'end}
local treasury={GetGoldBalance=function()
 w.goldReads=(w.goldReads or 0)+1
 if w.shiftGold and w.goldReads>1 then return w.gold+1 end
 return w.gold
end}
local religion={GetFaithBalance=function()return w.faith end}
local p={GetTreasury=function()return treasury end,GetReligion=function()return religion end,SetProperty=write}
local gi={GreatPersonClasses={GREAT_PERSON_CLASS_PROPHET={Index=0,GreatPersonClassType='GREAT_PERSON_CLASS_PROPHET'}},
 GreatPersonIndividuals={[0]={Index=0,GreatPersonClassType='GREAT_PERSON_CLASS_PROPHET'}}}
E={Game={GetLocalPlayer=function(...)assert(select('#',...)==0,'static player');return w.player or 0 end,
 GetCurrentGameTurn=function(...)
  assert(select('#',...)==0,'static turn');w.turnReads=(w.turnReads or 0)+1
  if w.shiftTurn and w.turnReads>1 then return w.turn+1 end
  return w.turn
 end,
 GetGreatPeople=function(...)assert(select('#',...)==0,'static people');return gp end},
 Players={[0]=p},PlayerConfigurations={[0]=cfg},GameInfo=gi,YieldTypes={GOLD=0,FAITH=5},
 UI={RequestPlayerOperation=write},CityManager={RequestOperation=write}}
'''


class ProphetPatronageDiagnosticTests(unittest.TestCase):
    def setUp(self):
        self.lua = LuaRuntime(unpack_returned_tuples=True)
        self.lua.execute(FIXTURE)
        source = Path(os.environ.get('BAIQI_PROPHET_QUOTE_SOURCE') or ROOT/'tools/lua/diagnostic_prophet_patronage.lua')
        self.module = self.lua.execute(source.read_text(encoding='utf-8'))
        self.w = self.lua.globals().W
        self.e = self.lua.globals().E

    def read(self, expected='KNOWN'):
        result = self.module.Read(self.e)
        self.assertEqual(result.status, expected)
        self.assertEqual(self.w.writes, 0)
        return result

    def test_exact_static_and_colon_ports_with_valid_zero_ids(self):
        result = self.read()
        self.assertEqual((result.turn,result.gold,result.faith),(180,500,300))
        self.assertEqual((len(result.quotes),result.quotes[1].individual),(1,0))
        self.assertFalse(result.quotes[1].canRecruit)
        self.assertEqual((result.quotes[1].goldCost,result.quotes[1].faithCost),(1200,800))

    def test_claimant_zero_is_claimed_and_receives_no_quote_calls(self):
        self.lua.execute('W.timeline[1].Claimant=0')
        self.assertEqual(len(self.read().quotes),0)
        self.assertEqual(self.w.quoteReads,0)

    def test_nil_cost_is_unknown_and_absent_instead_of_zero(self):
        self.w.goldCost = None
        quote = self.read().quotes[1]
        self.assertEqual(quote.goldCostStatus,'UNKNOWN')
        self.assertIsNone(quote.goldCost)

    def test_ui_sentinel_is_retained_without_payable_inference(self):
        self.w.faithCost = 1000000
        quote = self.read().quotes[1]
        self.assertEqual((quote.faithCostStatus,quote.faithCost),('KNOWN',1000000))
        self.assertFalse(quote.canFaith)

    def test_finite_fractional_cost_is_not_rounded(self):
        self.w.faithCost = 12.5
        self.assertEqual(self.read().quotes[1].faithCost,12.5)

    def test_invalid_or_object_cost_never_leaks_a_non_json_value(self):
        for value in ('0/0','math.huge','-1',"'1200'",'{}'):
            with self.subTest(value=value):
                self.setUp(); self.lua.execute('W.goldCost='+value)
                self.read('UNKNOWN')

    def test_unknown_eligibility_is_not_false(self):
        for key in ('canRecruit','canGold','canFaith'):
            with self.subTest(key=key):
                self.setUp(); self.w[key] = None
                self.read('UNKNOWN')

    def test_native_exception_returns_unknown_without_any_quote(self):
        self.w.throw = True
        self.read('UNKNOWN');self.assertEqual(self.w.quoteReads,0)

    def test_sparse_extra_and_zero_array_keys_are_rejected(self):
        for change in ('W.timeline[3]={Class=1}', 'W.timeline.extra=true', 'W.timeline[0]={Class=1}'):
            with self.subTest(change=change):
                self.setUp(); self.lua.execute(change)
                self.read('UNKNOWN')

    def test_oversize_timeline_is_bounded_before_quote_calls(self):
        self.lua.execute('for i=2,129 do W.timeline[i]={Class=1}end')
        self.read('UNKNOWN');self.assertEqual(self.w.quoteReads,0)

    def test_mismatched_individual_or_class_definition_is_unknown(self):
        for change in ('E.GameInfo.GreatPersonIndividuals[0].Index=1',
                       "E.GameInfo.GreatPersonIndividuals[0].GreatPersonClassType='WRONG'",
                       'E.GameInfo.GreatPersonClasses.GREAT_PERSON_CLASS_PROPHET.Index=math.huge'):
            with self.subTest(change=change):
                self.setUp();self.lua.execute(change);self.read('UNKNOWN')

    def test_duplicate_claimed_and_unclaimed_identity_is_unknown(self):
        self.lua.execute('W.timeline[2]={Class=0,Individual=0,Claimant=0}')
        self.read('UNKNOWN');self.assertEqual(self.w.quoteReads,0)

    def test_unknown_claimant_and_inherited_record_cannot_be_unclaimed(self):
        for change in ('W.timeline[1].Claimant=false',
                       'W.timeline[1]=setmetatable({}, {__index={Class=0,Individual=0}})',
                       'setmetatable(W.timeline,{})'):
            with self.subTest(change=change):
                self.setUp();self.lua.execute(change);self.read('UNKNOWN')

    def test_native_component_metatables_are_supported(self):
        self.lua.execute('setmetatable(E.Players[0],{});setmetatable(E.Game,{});setmetatable(E.PlayerConfigurations[0],{})')
        self.read()

    def test_non_prophet_empty_individual_is_not_a_phantom_prophet(self):
        self.lua.execute('W.timeline={{Class=1}}')
        self.assertEqual(len(self.read().quotes),0)
        self.assertEqual(self.w.quoteReads,0)

    def test_negative_gold_is_an_observation_but_invalid_faith_is_unknown(self):
        self.w.gold = -5
        self.assertEqual(self.read().gold,-5)
        self.setUp();self.w.faith = -1;self.read('UNKNOWN')

    def test_changed_turn_during_quote_read_is_unknown(self):
        self.w.shiftTurn = True;self.read('UNKNOWN')

    def test_changed_balance_during_quote_read_is_unknown(self):
        self.w.shiftGold = True;self.read('UNKNOWN')

    def test_wrong_player_leader_human_and_turn_are_rejected(self):
        for change in ('W.player=1', "W.leader='LEADER_TRAJAN'",'W.nonhuman=true','W.turn=178','W.turn=211'):
            with self.subTest(change=change):
                self.setUp();self.lua.execute(change);self.read('UNKNOWN')

    def test_returned_quote_is_detached_from_native_timeline(self):
        quote = self.read().quotes[1]
        quote.individual = 9;quote.canFaith = True
        self.assertEqual(self.w.timeline[1].Individual,0)
        self.assertFalse(self.w.canFaith)


if __name__ == '__main__':
    unittest.main()
