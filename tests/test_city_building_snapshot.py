from pathlib import Path
import unittest
from lupa.lua53 import LuaRuntime

ROOT=Path(__file__).resolve().parents[1]


class CityBuildingSnapshotTests(unittest.TestCase):
    def setUp(self):
        self.lua=LuaRuntime(unpack_returned_tuples=True)
        self.reader=self.lua.execute((ROOT/'tools/lua/city_building_snapshot.lua').read_text(encoding='utf-8'))
        self.env,self.w=self.lua.execute('''
local w={pid=0,turn=114,id=196610,owner=0,x=11,y=12,pop=9,slots=2,work=15,workType=3,
 leader='LEADER_BAIQI',multi=false,hotseat=false,reads=0,catalogReads=0,mutated=false}
w.rows={{Index=9,BuildingType='BUILDING_MUSEUM_ARTIFACT',IsWonder=false},
 {Index=1,BuildingType='BUILDING_TEST_WONDER',IsWonder=1},
 {Index=0,BuildingType='BUILDING_MONUMENT',IsWonder=0}}
local buildings={}
buildings.HasBuilding=function(_,index)
 w.reads=w.reads+1
 if w.mutation and not w.mutated then
  w.mutated=true
  if w.mutation=='turn' then w.turn=115
  elseif w.mutation=='owner' then w.owner=8
  elseif w.mutation=='id' then w.id=65539
  elseif w.mutation=='population' then w.pop=10 end
 end
 if w.nilPresence then return nil end
 return not w.largeCatalog
end
buildings.IsPillaged=function() return false end
buildings.GetNumGreatWorkSlots=function(_,index) return index==9 and w.slots or 0 end
buildings.GetGreatWorkInSlot=function(_,index,slot) return slot==0 and w.work or -1 end
buildings.GetGreatWorkTypeFromIndex=function() return w.workType end
local city={GetID=function()return w.id end,GetOwner=function()return w.owner end,
 GetX=function()return w.x end,GetY=function()return w.y end,
 GetPopulation=function()return w.pop end,GetBuildings=function()return buildings end}
local env={Game={GetLocalPlayer=function()return w.pid end,GetCurrentGameTurn=function()return w.turn end},
 GameConfiguration={IsAnyMultiplayer=function()return w.multi end,IsHotseat=function()return w.hotseat end},
 PlayerConfigurations={[0]={GetLeaderTypeName=function()return w.leader end}},
 Players={[0]={GetCities=function()return {FindID=function(_,id)if id==196610 then return city end end} end}},
 GameInfo={Buildings=function()
  local i=0
  return function()
   i=i+1
   if w.largeCatalog then
    w.catalogReads=w.catalogReads+1
    return {Index=i,BuildingType='BUILDING_EXTRA_'..i,IsWonder=false}
   end
   return w.rows[i]
  end
 end}}
w.buildings=buildings
return env,w
''')

    def read(self):
        return self.reader.Read(self.env,196610)

    def test_complete_sorted_inventory_preserves_work_identity_and_empty_slot(self):
        result,error=self.read()
        self.assertIsNone(error)
        self.assertEqual((result.turn,result.player_id,result.city_id,result.x,result.y,result.population),
                         (114,0,196610,11,12,9))
        self.assertEqual([row.index for row in result.buildings.values()],[0,1,9])
        self.assertFalse(result.buildings[1].is_wonder)
        self.assertTrue(result.buildings[2].is_wonder)
        museum=result.buildings[3]
        self.assertEqual((museum.type,museum.pillaged,museum.slot_count),('BUILDING_MUSEUM_ARTIFACT',False,2))
        self.assertEqual((museum.slots[1].slot,museum.slots[1].work,museum.slots[1].type_index),(0,15,3))
        self.assertEqual((museum.slots[2].slot,museum.slots[2].work,museum.slots[2].type_index),(1,-1,None))
        self.w.work=22
        self.w.rows[1].BuildingType='CHANGED_NATIVE_ROW'
        self.assertEqual((museum.type,museum.slots[1].work),('BUILDING_MUSEUM_ARTIFACT',15))

    def test_unknown_presence_metadata_or_reader_rejects_entire_snapshot(self):
        for change in ('presence','metadata','reader'):
            with self.subTest(change=change):
                self.setUp()
                if change=='presence':self.w.nilPresence=True
                elif change=='metadata':self.w.workType=None
                else:self.w.buildings.GetGreatWorkInSlot=None
                self.assertEqual(self.read(),(None,'READ_FAILED'))

    def test_identity_or_turn_change_during_getter_rejects_mixed_snapshot(self):
        for change in ('turn','owner','id','population'):
            with self.subTest(change=change):
                self.setUp()
                self.w.mutation=change
                self.assertEqual(self.read(),(None,'READ_FAILED'))
                self.assertTrue(self.w.mutated)

    def test_invalid_capacity_duplicate_nonfinite_and_unbounded_catalog_fail(self):
        for change in ('slots','duplicate','nonfinite','catalog'):
            with self.subTest(change=change):
                self.setUp()
                if change=='slots':self.w.slots=65
                elif change=='duplicate':self.w.rows[4]=self.w.rows[1]
                elif change=='nonfinite':self.w.rows[1].Index=float('inf')
                else:self.w.largeCatalog=True
                self.assertEqual(self.read(),(None,'READ_FAILED'))
                if change=='catalog':self.assertEqual(self.w.catalogReads,4097)
