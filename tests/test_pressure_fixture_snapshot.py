"""Synthetic ports and actual strict consumer; no live game reads or actions."""
import copy
import importlib
import json
from pathlib import Path
import unittest
from tools.qualify_pressure_geometry import qualify_pressure_geometry
from tests.test_pressure_fixture_geometry import LAYOUT

SOURCE=(Path(__file__).resolve().parents[1]/'tools/lua/pressure_fixture_snapshot.lua').read_text(encoding='utf-8')
PORTS='''function(layout)
 local E={variant='NO_SITE',setup_stage='READY',contents=0,members=0,turnCalls=0,visibleCalls=0}
 local slots={};for _,s in ipairs(layout.slots)do slots[s.x+44*s.y]=s.owner end
 E.MapConfiguration={GetValue=function(key)assert(key=='MAP_SCRIPT');return
  '{e8b15363-c9b9-4dcb-b575-117d9308d426}Maps/P6PressureNoSite.lua' end}
 E.GetTurn=function()E.turnCalls=E.turnCalls+1;return E.changedTurn and E.turnCalls or 0 end
 E.Map={GetGridSize=function()return 44,26 end,GetPlotByIndex=function(i)
  return {GetIndex=function()return i end,GetX=function()return i%44 end,GetY=function()return math.floor(i/44)end,
   IsWater=function()E.contents=E.contents+1;return E.variant~='MANY' and E.bareAt~=i and slots[i]==nil end,
   IsCity=function()E.contents=E.contents+1;return (slots[i]~=nil)~=(E.badCityAt==i) end,
   GetOwner=function()E.contents=E.contents+1;assert(slots[i]~=nil);return E.wrongOwnerAt==i and 1 or slots[i] end}
 end}
 E.Visibility={IsVisible=function(self,x,y)
  E.visibleCalls=E.visibleCalls+1;return x+44*y~=E.invisibleAt end}
 E.Players={}
 for owner=0,1 do local own=owner;local array={}
  for _,s in ipairs(layout.slots)do if s.owner==own then local slot=s;local id=#array
   array[#array+1]={GetOwner=function()return own end,GetID=function()return E.duplicateIDs and 0 or id end,
    GetX=function()return slot.x end,GetY=function()return slot.y end}
  end end
  local collection={GetCount=function()return #array end,Members=function()
   E.members=E.members+1;return function(state,last)local n=last+1
    if n<=#state then return n,state[n]end end,array,0 end}
  E.Players[own]={GetCities=function()return collection end}
 end
 return E
end'''


class PressureFixtureSnapshotTests(unittest.TestCase):
    def ports(self,version='lua51',layout=None):
        lua=importlib.import_module('lupa.'+version).LuaRuntime(unpack_returned_tuples=True)
        data=lua.table_from(LAYOUT if layout is None else layout,recursive=True)
        return lua,lua.execute(SOURCE),lua.eval(PORTS)(data),data

    def python_snapshot(self,s):
        root={k:s[k] for k in ('source','fixture_id','variant','setup_stage','turn','width','height')}
        root['cities']=[dict(c) for c in s.cities.values()]
        root['plots']=[{k:p[k] for k in ('index','x','y','water','city','visible','owner')} for p in s.plots.values()]
        return root

    def test_full_snapshot_dual_lua_and_actual_python_consumer(self):
        for version in ('lua51','lua53'):
            lua,collect,env,layout=self.ports(version);result=self.python_snapshot(collect(env,layout))
            self.assertEqual(qualify_pressure_geometry(result,LAYOUT)['status'],'QUALIFIED_NO_ADMISSIBLE_GEOMETRY')
            self.assertEqual((env.visibleCalls,env.members,env.turnCalls),(1144,2,2))
            self.assertIsNone(result['plots'][0]['owner'])
            self.assertEqual([c['id'] for c in result['cities'] if c['owner']==1],[0])
            self.assertEqual([dict(layout.slots[i]) for i in range(1,12)],LAYOUT['slots'])

    def test_late_unknown_visibility_reads_no_contents_or_cities(self):
        lua,collect,env,layout=self.ports();env.invisibleAt=1143
        with self.assertRaisesRegex(Exception,'Entire map'):collect(env,layout)
        self.assertEqual((env.contents,env.members,env.visibleCalls),(0,0,1144))

    def test_many_map_returns_geometry_without_candidate_claim(self):
        for version in ('lua51','lua53'):
            lua,collect,env,layout=self.ports(version);env.variant='MANY'
            env.MapConfiguration.GetValue=lua.eval("function()return '{e8b15363-c9b9-4dcb-b575-117d9308d426}Maps/P6PressureMany.lua'end")
            result=qualify_pressure_geometry(self.python_snapshot(collect(env,layout)),LAYOUT)
            self.assertEqual(result['status'],'READY_MANY_GEOMETRY_ONLY')
            self.assertIsNone(result['global_no_admissible_geometry'])
            self.assertIsNone(result['many_candidate_pressure'])

    def test_wrong_world_or_setup_guard_before_contents(self):
        for mutation in ["e.MapConfiguration.GetValue=function()return 'Continents.lua'end",
                         'e.Map.GetGridSize=function()return 74,46 end',"e.setup_stage='PREP'",
                         'e.variant=false']:
            lua,collect,env,layout=self.ports();lua.eval('function(e)'+mutation+' end')(env)
            with self.assertRaises(Exception):collect(env,layout)
            self.assertEqual((env.contents,env.members,env.visibleCalls),(0,0,0))

    def test_bad_city_state_and_changed_turn_fail(self):
        for key,value in [('duplicateIDs',True),('badCityAt',180),('wrongOwnerAt',180),('changedTurn',True)]:
            lua,collect,env,layout=self.ports();env[key]=value
            with self.subTest(key=key),self.assertRaises(Exception):collect(env,layout)

    def test_malformed_layout_and_valid_terrain_mismatch(self):
        for key,value in [('x',4.5),('owner',False),('start',1),('extra',0)]:
            data=copy.deepcopy(LAYOUT);data['slots'][0][key]=value
            lua,collect,env,layout=self.ports(layout=data)
            with self.assertRaises(Exception):collect(env,layout)
            self.assertEqual((env.contents,env.members),(0,0))
        lua,collect,env,layout=self.ports();env.bareAt=0
        result=self.python_snapshot(collect(env,layout))
        self.assertEqual(qualify_pressure_geometry(result,LAYOUT)['status'],'NOT_QUALIFIED')
