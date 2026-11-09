from pathlib import Path
import unittest
from lupa.lua51 import LuaRuntime

ROOT=Path(__file__).resolve().parents[1]


class MissionarySnapshotTests(unittest.TestCase):
    def setUp(self):
        self.lua=LuaRuntime(unpack_returned_tuples=True)
        self.lua.execute('''
W={turn=131,faith=200,created=1,pop=4,majority=-1,owner=0,list={{Religion=0,Followers=1},{Religion=1,Followers=2}},units={},cityReads=0}
local cfg={IsHuman=function()return true end,GetLeaderTypeName=function()return 'LEADER_BAIQI'end}
local city={GetOwner=function()return W.owner end,GetID=function()return 0 end,GetX=function()return 0 end,GetY=function()return 0 end,GetPopulation=function()return W.pop end,GetReligion=function()W.cityReads=W.cityReads+1;return {GetMajorityReligion=function()return W.majority end,GetReligionsInCity=function()if W.change then W.faith=W.faith+1 end;return W.list end}end}
local p={IsTurnActive=function()return not W.inactive end,GetReligion=function()return {GetReligionTypeCreated=function()return W.created end,GetFaithBalance=function()return W.faith end}end,GetCities=function()return {GetCount=function()return 1 end,Members=function()return ipairs({city})end}end,GetUnits=function()return {Members=function()return ipairs(W.units)end}end}
E={Game={GetCurrentGameTurn=function()return W.turn end,GetLocalPlayer=function()return 0 end,IsAllowStrategicCommands=function()return true end},GameConfiguration={IsAnyMultiplayer=function()return W.multi==true end},UI={IsGameCoreBusy=function()return false end,IsProcessingMessages=function()return false end},PlayerConfigurations={[0]=cfg},Players={[0]=p},GameInfo={Units={[0]={UnitType='UNIT_MISSIONARY'}}}}
function AddMissionary()W.units={{GetOwner=function()return 0 end,GetID=function()return 0 end,GetUnitType=function()return 0 end,IsDelayedDeath=function()return false end,GetX=function()return 0 end,GetY=function()return 0 end,GetReligionType=function()return 1 end,GetSpreadCharges=function()return 3 end,GetMovesRemaining=function()return 4 end,GetFormationUnitCount=function()return 1 end}}end
''')
        self.m=self.lua.execute((ROOT/'tools/lua/diagnostic_missionary_snapshot.lua').read_text(encoding='utf-8'))

    def read(self):return self.m.Read(self.lua.globals().E)

    def test_zero_missionaries_and_unconverted_city_are_known(self):
        r=self.read();self.assertEqual(r.status,'KNOWN');self.assertEqual(len(r.rows),4)

    def test_actual_ui_flat_unit_ports_and_zero_ids_are_used(self):
        self.lua.execute('AddMissionary()');r=self.read();self.assertEqual(r.status,'KNOWN');self.assertEqual(list(r.rows[5].values()),['UNIT',0,0,0,1,3,4,1])

    def test_native_unaffiliated_minus_one_and_zero_follower_rows_are_retained(self):
        self.lua.execute('W.list={{Religion=-1,Followers=3},{Religion=1,Followers=1},{Religion=8,Followers=0}}')
        r=self.read();self.assertEqual(r.status,'KNOWN');self.assertEqual(list(r.rows[3].values()),['FOLLOWER',0,-1,3]);self.assertEqual(list(r.rows[5].values()),['FOLLOWER',0,8,0])

    def test_changed_faith_unknown_without_partial_rows(self):
        self.lua.execute('W.change=true');r=self.read();self.assertEqual(r.status,'UNKNOWN');self.assertIsNone(r.rows)

    def test_foreign_owner_rejected_before_city_religion(self):
        self.lua.execute('W.owner=1');self.assertEqual(self.read().status,'UNKNOWN');self.assertEqual(self.lua.globals().W.cityReads,0)

    def test_sparse_duplicate_or_impossible_followers_are_unknown(self):
        for s in ('W.list[3]=W.list[2];W.list[2]=nil','W.list[2].Religion=0','W.list[2].Followers=4','W.faith=math.huge'):
            with self.subTest(s=s):self.setUp();self.lua.execute(s);self.assertEqual(self.read().status,'UNKNOWN')

    def test_multiplayer_inactive_and_duplicate_unit_are_unknown(self):
        for s in ('W.multi=true','W.inactive=true','AddMissionary();W.units[2]=W.units[1]'):
            with self.subTest(s=s):self.setUp();self.lua.execute(s);self.assertEqual(self.read().status,'UNKNOWN')


if __name__=='__main__':unittest.main()
