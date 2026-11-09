"""Native public standings fallback uses actual product helper; no game orders."""
from pathlib import Path
import os
import unittest
from lupa.lua51 import LuaRuntime

ROOT=Path(__file__).resolve().parents[1]
FIXTURE=r'''
W={turn=187,ids={0,1,2,3,4,5},classes={{Index=0,MaxPlayerInstances=1},{Index=1,MaxPlayerInstances=-1}},
 scope=true,display=0,localID=0,nativeCalls=0,playerReads=0,pointReads=0,writes=0}
Game={GetCurrentGameTurn=function(...)assert(select('#',...)==0);return W.turn end,
 GetLocalPlayer=function(...)assert(select('#',...)==0);return W.localID end,
 GetGreatPeople=function(...)assert(select('#',...)==0);return {
  CountPeopleReceivedByPlayer=function(self,cid,pid)assert(type(self)=='table');return 0 end}end}
GameInfo={GreatPersonClasses=function()
 local i=0;return function()i=i+1;return W.classes[i]end end}
GetDisplayPlayerID=function()return W.display end
BaiqiUIGuard={PlayerID=function()if W.scope then return 0 end end}
Players={};PlayerConfigurations={};Locale={Lookup=function(k)assert(type(k)=='string');return k end}
for pid=0,5 do
 local id=pid
 Players[id]={GetID=function()return id end,GetDiplomacy=function()return {HasMet=function(_,other)return other==2 end}end,
  GetGreatPeoplePoints=function()return {
   GetPointsTotal=function(self,cid)
    assert(type(self)=='table');W.pointReads=W.pointReads+1
    if W.badClass==cid then error('native point read unavailable')end
    if W.nan then return 0/0 end
    if W.mutate then W.turn=W.turn+1 end
    if W.removeScope then W.scope=false end
    if W.changeData then W.data.PointsByClass[0]={external=true}end
    return id==0 and 42 or 100-id
   end,
   GetPointsPerTurn=function(self,cid)assert(type(self)=='table');return W.negativeRate and -1 or 1 end}end}
 PlayerConfigurations[id]={GetCivilizationShortDescription=function()return 'CIV_'..id end}
end
PlayerManager={GetAliveMajors=function(...)
 assert(select('#',...)==0);W.playerReads=W.playerReads+1
 if W.throwPlayers then error('players unavailable')end
 local out={};for k,id in pairs(W.ids)do out[k]=Players[id]end
 if W.metaPlayers then setmetatable(out,{})end
 return out
end}
PopulateData=function(data,isPast)
 W.nativeCalls=W.nativeCalls+1;W.lastPast=isPast
 if W.nativeError then error('originalPopulateDataFailure')end
 data.original=true
end
UI={RequestPlayerOperation=function()W.writes=W.writes+1;error('forbidden game order')end}
data={PointsByClass={[0]={},[1]={}}};W.data=data
'''


class GPViewDataTests(unittest.TestCase):
    def setUp(self):
        self.lua=LuaRuntime(unpack_returned_tuples=True)
        self.lua.execute(FIXTURE)
        path=Path(os.environ.get('BAIQI_GP_VIEW_DATA_SOURCE') or ROOT/'mod/Baiqi/Lua/BaiqiGPViewData.lua')
        self.lua.execute(path.read_text(encoding='utf-8'))
        self.w=self.lua.globals().W;self.data=self.lua.globals().data
        self.m=self.lua.globals().BaiqiGPViewData

    def fill(self,expected):
        self.assertEqual(self.m.Fill(self.data),expected)
        self.assertEqual(self.w.writes,0)

    def test_known_six_players_restore_exact_public_fields_and_private_names_stay_unmet(self):
        self.fill(True)
        for cid,maximum in ((0,1),(1,-1)):
            rows=self.data.PointsByClass[cid]
            self.assertEqual(len(rows),6)
            own=rows[1]
            self.assertEqual((own.PlayerID,own.IsPlayer,own.PointsTotal,own.PointsPerTurn,own.NumInstancesEarned,own.MaxPlayerInstances),(0,True,42,1,0,maximum))
            by_id={rows[i].PlayerID:rows[i]for i in range(1,7)}
            self.assertEqual(by_id[2].PlayerName,'CIV_2')
            self.assertEqual(by_id[1].PlayerName,'LOC_DIPLOPANEL_UNMET_PLAYER')
            self.assertEqual([rows[i].PlayerID for i in range(1,7)],[0,1,2,3,4,5])

    def test_existing_populated_class_is_preserved_while_empty_class_is_filled(self):
        self.lua.execute('originalRow={custom=true};originalClass={originalRow};data.PointsByClass[0]=originalClass')
        self.fill(True)
        self.assertTrue(self.lua.eval('data.PointsByClass[0]==originalClass and data.PointsByClass[0][1]==originalRow'))
        self.assertEqual(len(self.data.PointsByClass[1]),6)

    def test_missing_or_all_populated_classes_do_not_invent_data(self):
        for change in ('data.PointsByClass={}','data.PointsByClass={[0]={{native=true}},[1]={{native=true}}}'):
            with self.subTest(change=change):
                self.setUp();self.lua.execute(change);self.fill(False)
                self.assertEqual(self.w.playerReads,0)

    def test_non_baiqi_and_display_or_local_mismatch_do_not_read_players(self):
        for key,value in (('scope',False),('display',1),('localID',1)):
            with self.subTest(key=key):
                self.setUp();self.w[key]=value;self.fill(False)
                self.assertEqual(self.w.playerReads,0)

    def test_exception_in_second_class_does_not_publish_first_class(self):
        self.w.badClass=1;self.fill(False)
        self.assertEqual(len(self.data.PointsByClass[0]),0)
        self.assertEqual(len(self.data.PointsByClass[1]),0)

    def test_nan_or_negative_points_data_is_unknown(self):
        for key in ('nan','negativeRate'):
            with self.subTest(key=key):
                self.setUp();self.w[key]=True;self.fill(False)
                self.assertEqual(len(self.data.PointsByClass[0]),0)

    def test_sparse_duplicate_missing_own_and_metatable_player_lists_are_unknown(self):
        changes=('W.ids={[2]=0}','W.ids={0,0}','W.ids={1,2}','W.metaPlayers=true','W.ids={}')
        for change in changes:
            with self.subTest(change=change):
                self.setUp();self.lua.execute(change);self.fill(False)
                self.assertEqual(len(self.data.PointsByClass[0]),0)

    def test_class_limit_and_duplicate_class_stop_without_publication(self):
        for change in ('W.classes[2].Index=0','for i=1,65 do W.classes[i]={Index=i}end;data.PointsByClass[1]={}'):
            with self.subTest(change=change):
                self.setUp();self.lua.execute(change);self.fill(False)
                self.assertEqual(len(self.data.PointsByClass[0]),0)

    def test_turn_scope_or_data_change_during_reads_does_not_commit(self):
        for key in ('mutate','removeScope','changeData'):
            with self.subTest(key=key):
                self.setUp();self.w[key]=True;self.fill(False)
                self.assertEqual(len(self.data.PointsByClass[1]),0)

    def test_original_population_runs_first_and_error_is_propagated(self):
        self.assertTrue(self.m.Install())
        self.lua.globals().PopulateData(self.data,False)
        self.assertEqual(self.w.nativeCalls,1);self.assertTrue(self.data.original)
        self.assertEqual(len(self.data.PointsByClass[0]),6)
        self.setUp();self.m.Install();self.w.nativeError=True
        with self.assertRaisesRegex(Exception,'originalPopulateDataFailure'):
            self.lua.globals().PopulateData(self.data,False)
        self.assertEqual(self.w.nativeCalls,1)
        self.assertEqual(self.w.playerReads,0)

    def test_past_view_and_normal_leader_keep_original_data_only(self):
        self.m.Install();self.lua.globals().PopulateData(self.data,True)
        self.assertEqual(self.w.nativeCalls,1);self.assertEqual(self.w.playerReads,0)
        self.w.scope=False;self.lua.globals().PopulateData(self.data,False)
        self.assertEqual(self.w.nativeCalls,2);self.assertEqual(self.w.playerReads,0)

    def test_missing_original_handlers_do_not_install_a_fake_page(self):
        self.lua.execute('PopulateData=nil')
        self.assertFalse(self.m.Install())
        self.assertIsNone(self.lua.globals().PopulateData)
        self.assertEqual(self.w.writes,0)


if __name__=='__main__':
    unittest.main()
