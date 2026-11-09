"""The native empty current class is distinct from missing or malformed data."""
from pathlib import Path
import os
import unittest
from lupa.lua51 import LuaRuntime

ROOT=Path(__file__).resolve().parents[1]
FIXTURE=r'''
W={turn=187,current={{Class=0}},past={{Class=0,Individual=0,Claimant=0,TurnGranted=0}},
 created=-1,earned=0,held=false,faith=500,points=41,rate=1,writes=0}
local w=W
local r={GetReligionTypeCreated=function()return w.created end,GetNumBeliefsEarned=function()return w.earned end,
 HasReligiousFoundingUnit=function()return w.held end,GetFaithBalance=function()return w.faith end,
 GetPantheon=function()return 20 end}
local pts={GetPointsTotal=function(_,id)assert(id==0);if w.throwPoints then error('points unavailable')end;return w.points end,
 GetPointsPerTurn=function(_,id)assert(id==0);return w.rate end}
local p={GetReligion=function()return r end,GetGreatPeoplePoints=function()return pts end,
 SetProperty=function()w.writes=w.writes+1;error('write')end}
local cfg={IsHuman=function()return not w.nonhuman end,GetLeaderTypeName=function()return w.leader or'LEADER_BAIQI'end}
local gp={GetTimeline=function()
 if w.throwCurrent then error('current unavailable')end
 return w.current
end,GetPastTimeline=function()
 if w.throwPast then error('past unavailable')end
 if w.changeOwn then w.points=w.points+1 end
 return w.past
end}
E={Game={GetCurrentGameTurn=function(...)assert(select('#',...)==0,'static turn');w.turnReads=(w.turnReads or 0)+1;if w.changeTurn and w.turnReads>1 then return w.turn+1 end;return w.turn end,
 GetLocalPlayer=function(...)assert(select('#',...)==0,'static player');return w.player or 0 end,
 GetGreatPeople=function(...)assert(select('#',...)==0,'static people');return gp end},
 Players={[0]=p},PlayerConfigurations={[0]=cfg},
 GameInfo={GreatPersonClasses={GREAT_PERSON_CLASS_PROPHET={Index=0,GreatPersonClassType='GREAT_PERSON_CLASS_PROPHET'}},
 GreatPersonIndividuals={[0]={Index=0,GreatPersonClassType='GREAT_PERSON_CLASS_PROPHET'}}}}
'''


class ProphetSupplyTests(unittest.TestCase):
    def setUp(self):
        self.lua=LuaRuntime(unpack_returned_tuples=True)
        self.lua.execute(FIXTURE)
        source=Path(os.environ.get('BAIQI_PROPHET_SUPPLY_SOURCE') or ROOT/'tools/lua/diagnostic_prophet_supply.lua')
        self.module=self.lua.execute(source.read_text(encoding='utf-8'))
        self.w=self.lua.globals().W;self.e=self.lua.globals().E

    def read(self,status='KNOWN'):
        result=self.module.Read(self.e)
        self.assertEqual(result.status,status);self.assertEqual(self.w.writes,0)
        return result

    def test_valid_empty_class_and_zero_past_identity(self):
        result=self.read()
        self.assertEqual(result.current.supplyState,'NONE_AVAILABLE')
        self.assertEqual((result.pastProphets[1].individual,result.pastProphets[1].claimant,result.pastProphets[1].turnGranted),(0,0,0))
        self.assertEqual((result.own.created,result.own.points,result.own.perTurn),(-1,41,1))

    def test_unclaimed_zero_individual_is_not_none_available(self):
        self.lua.execute('W.current[1].Individual=0')
        result=self.read();self.assertEqual(result.current.supplyState,'UNCLAIMED')
        self.assertEqual(result.current.individual,0)

    def test_claimant_zero_is_claimed(self):
        self.lua.execute('W.current[1].Individual=0;W.current[1].Claimant=0')
        result=self.read();self.assertEqual(result.current.supplyState,'CLAIMED')
        self.assertEqual(result.current.claimant,0)

    def test_missing_and_duplicate_current_classes_are_unknown(self):
        for value in ('{}','{{Class=0},{Class=0}}'):
            with self.subTest(value=value):
                self.setUp();self.lua.execute('W.current='+value);self.read('UNKNOWN')

    def test_claimant_without_individual_is_unknown(self):
        self.lua.execute('W.current[1].Claimant=0');self.read('UNKNOWN')

    def test_sparse_extra_zero_and_oversize_current_arrays(self):
        for change in ('W.current[3]={Class=1}','W.current.extra=true','W.current[0]={Class=1}',
                       'for i=2,129 do W.current[i]={Class=1}end'):
            with self.subTest(change=change):
                self.setUp();self.lua.execute(change);self.read('UNKNOWN')

    def test_metatable_lists_and_records_are_not_factual_rows(self):
        for change in ('setmetatable(W.current,{})',
                       'W.current[1]=setmetatable({}, {__index={Class=0}})',
                       'setmetatable(W.past,{})'):
            with self.subTest(change=change):
                self.setUp();self.lua.execute(change);self.read('UNKNOWN')

    def test_native_object_metatables_remain_supported(self):
        self.lua.execute('setmetatable(E.Game,{});setmetatable(E.Players[0],{});setmetatable(E.GameInfo,{})')
        self.read()

    def test_mismatched_current_individual_definition(self):
        for change in ('E.GameInfo.GreatPersonIndividuals[0].Index=1',
                       "E.GameInfo.GreatPersonIndividuals[0].GreatPersonClassType='WRONG'"):
            with self.subTest(change=change):
                self.setUp();self.lua.execute('W.current[1].Individual=0;'+change);self.read('UNKNOWN')

    def test_past_unclaimed_entries_are_filtered_like_original_tab(self):
        self.lua.execute('W.past={{Class=0,Individual=0}}')
        self.assertEqual(len(self.read().pastProphets),0)

    def test_empty_past_does_not_invent_historical_claims(self):
        self.w.past=self.lua.table()
        self.assertEqual(len(self.read().pastProphets),0)

    def test_duplicate_claimed_past_identity_is_unknown(self):
        self.lua.execute('W.past[2]={Class=0,Individual=0,Claimant=1}')
        self.read('UNKNOWN')

    def test_invalid_claimant_and_future_past_turn_are_unknown(self):
        for change in ('W.past[1].Claimant=-1','W.past[1].Claimant=false',
                       'W.past[1].TurnGranted=188','W.past[1].TurnGranted=math.huge'):
            with self.subTest(change=change):
                self.setUp();self.lua.execute(change);self.read('UNKNOWN')

    def test_optional_unknown_past_turn_is_not_zero(self):
        self.w.past[1].TurnGranted=None
        self.assertIsNone(self.read().pastProphets[1].turnGranted)

    def test_non_prophet_empty_individual_is_ignored(self):
        self.lua.execute('W.current[2]={Class=1};W.past[2]={Class=1}')
        self.assertEqual(len(self.read().pastProphets),1)

    def test_negative_own_faith_points_rate_and_invalid_status_are_unknown(self):
        for key,value in (('faith',-1),('points',-1),('rate',-1),('earned',-1),('created',-2),('held',None)):
            with self.subTest(key=key):
                self.setUp();self.w[key]=value;self.read('UNKNOWN')

    def test_changed_own_snapshot_or_turn_is_unknown(self):
        for key in ('changeOwn','changeTurn'):
            with self.subTest(key=key):
                self.setUp();self.w[key]=True;self.read('UNKNOWN')

    def test_exceptions_and_wrong_local_context_remain_unknown(self):
        for key,value in (('throwCurrent',True),('throwPast',True),('throwPoints',True),
                          ('player',1),('nonhuman',True),('turn',98),('turn',251)):
            with self.subTest(key=key):
                self.setUp();self.w[key]=value;self.read('UNKNOWN')

    def test_past_array_bounds_and_extra_keys(self):
        for change in ('W.past.extra=true','W.past[3]={Class=1}',
                       'for i=2,513 do W.past[i]={Class=1}end'):
            with self.subTest(change=change):
                self.setUp();self.lua.execute(change);self.read('UNKNOWN')

    def test_fresh_results_are_detached(self):
        result=self.read();result.pastProphets[1].claimant=2;result.own.points=99
        self.assertEqual(self.w.past[1].Claimant,0);self.assertEqual(self.w.points,41)


if __name__=='__main__':
    unittest.main()
