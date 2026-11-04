from pathlib import Path
import unittest
from lupa.lua53 import LuaRuntime

ROOT = Path(__file__).resolve().parents[1]
SOURCE = (ROOT / 'tools/lua/normal_training_snapshot.lua').read_text(encoding='utf-8')
FIXTURE = '''
T={turn=101,city=196610,progress=0,cost=200,gold=-3.25,size=1,hash=1011336245,
 head={UnitType=8},units={},pid=0,multi=false,leader='LEADER_BAIQI',writes=0}
local queue={GetSize=function() return T.size end,
 GetCurrentProductionTypeHash=function() return T.hash end,
 GetUnitProgress=function(_,i) assert(i==8);return T.progress end,
 GetUnitCost=function(_,i) assert(i==8);return T.cost end,
 GetAt=function(_,i) assert(i==0);return T.head end}
local city={GetID=function() return T.city end,GetPopulation=function() return 8 end,
 GetYield=function(_,i) assert(i==3);return 27.5 end,GetBuildQueue=function() return queue end}
local units={Members=function() return ipairs(T.units) end}
local cities={FindID=function(_,i) assert(i==196610);return city end}
local player={GetCities=function() return cities end,GetUnits=function() return units end,
 GetTreasury=function() return {GetGoldBalance=function() return T.gold end} end}
E={Game={GetLocalPlayer=function() return T.pid end,GetCurrentGameTurn=function() return T.turn end},
 GameConfiguration={IsAnyMultiplayer=function() return T.multi end},
 PlayerConfigurations={[0]={GetLeaderTypeName=function() return T.leader end}},
 Players={[0]=player},GameInfo={Units={UNIT_ARCHAEOLOGIST={Index=8,Hash=1011336245}}},
 YieldTypes={PRODUCTION=3}}
function Unit(id,kind,home,owner)
 return {GetID=function() return id end,GetUnitType=function() return kind end,
 GetOwner=function() return owner or 0 end,GetX=function() return 9 end,
 GetY=function() return 15 end,GetMovesRemaining=function() return 4 end,
 GetArchaeologyHomeCity=function() return home end}
end
-- Any attempted game write would fail this fixture rather than silently succeed.
E.UI=setmetatable({},{__index=function() T.writes=T.writes+1;error('write') end})
'''


class NormalTrainingSnapshotTests(unittest.TestCase):
    def context(self, source=SOURCE):
        lua=LuaRuntime(unpack_returned_tuples=True)
        lua.execute(FIXTURE)
        return lua,lua.execute(source)

    def test_zero_progress_signed_balance_sorted_full_ids_and_unassigned_home(self):
        lua,module=self.context()
        lua.execute('T.units={Unit(5898281,8,196610),Unit(12,8,-1),Unit(17,1,-1)}')
        v,err=module.Read(lua.globals().E,196610)
        self.assertIsNone(err)
        self.assertEqual((v.turn,v.unit_progress,v.unit_cost,v.gold),(101,0,200,-3.25))
        self.assertEqual((v.head.unit_index,len(v.archaeologists)),(8,2))
        self.assertEqual((v.archaeologists[1].id,v.archaeologists[1].home_city),(12,-1))
        self.assertEqual(lua.globals().T.writes,0)

    def test_empty_queue_and_modified_cost_are_observations(self):
        lua,module=self.context()
        lua.execute('T.size=0;T.hash=0;T.head=nil;T.cost=231.5')
        v,err=module.Read(lua.globals().E,196610)
        self.assertIsNone(err)
        self.assertIsNone(v.head)
        self.assertEqual((v.unit_cost,len(v.archaeologists)),(231.5,0))

    def test_unknown_provider_or_throw_rejects_entire_snapshot(self):
        for mutation in ['E=nil','E.Players=nil','E.Game.GetLocalPlayer=function() error("private") end',
                         'E.Players[0].GetUnits=function() error("late read") end']:
            with self.subTest(mutation=mutation):
                lua,module=self.context();lua.execute(mutation)
                self.assertEqual(module.Read(lua.globals().E,196610),(None,'READ_FAILED'))

    def test_wrong_identity_and_full_id_alias_rejected(self):
        for mutation in ['T.pid=1','T.multi=true','T.multi=nil','T.leader="LEADER_GORGO"','T.city=65538']:
            with self.subTest(mutation=mutation):
                lua,module=self.context();lua.execute(mutation)
                self.assertEqual(module.Read(lua.globals().E,196610),(None,'READ_FAILED'))

    def test_malformed_numeric_fields_and_head_do_not_become_success(self):
        for mutation in ['T.cost=0/0','T.progress=-1','T.hash=true','T.head={UnitType="8"}',
                         'T.head=false','T.units={Unit(2,8,"-1")}','T.units={Unit(2,8,-1,1)}',
                         'T.units={Unit(2,8,-1),Unit(2,8,-1)}','T.units={Unit(2,nil,-1)}']:
            with self.subTest(mutation=mutation):
                lua,module=self.context();lua.execute(mutation)
                self.assertEqual(module.Read(lua.globals().E,196610),(None,'READ_FAILED'))

    def test_native_like_provider_indexing_and_no_global_mutation(self):
        lua,module=self.context()
        lua.execute('''
local original=E.Players[0]
E.Players[0]=setmetatable({},{__index=function(_,key) return original[key] end})
before={};for k in pairs(_G) do before[k]=true end
''')
        v,err=module.Read(lua.globals().E,196610)
        self.assertIsNone(err);self.assertEqual(v.city_id,196610)
        lua.execute('for k in pairs(_G) do assert(before[k]) end;assert(T.writes==0)')


if __name__=='__main__':unittest.main()
