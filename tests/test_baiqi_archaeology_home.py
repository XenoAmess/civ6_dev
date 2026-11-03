from pathlib import Path
import json
import unittest
from lupa.lua53 import LuaRuntime

ROOT = Path(__file__).resolve().parents[1]


class ArchaeologyHomeTests(unittest.TestCase):
    def setUp(self):
        self.lua = LuaRuntime(unpack_returned_tuples=True)
        self.lua.execute('''
          H={pid=7,unitID=4,unitOwner=7,unitType='UNIT_ARCHAEOLOGIST',homeCityID=66,
            cityOwner=7,cityX=2,cityY=3,buildingIndex=10,buildingPresent=true,
            buildingPillaged=false,slotCount=3,slotWorks={-1,101,-1},
            slotTypes={'GREATWORKSLOT_ARTIFACT','GREATWORKSLOT_ARTIFACT','GREATWORKSLOT_ARTIFACT'},
            slotReads=0,finds=0}
          local h=H
          local unit={GetID=function() return h.unitID end,GetOwner=function() return h.unitOwner end,
            GetUnitType=function() return h.badType or 19 end,
            GetArchaeologyHomeCity=function() return h.homeCityID end}
          local buildings={HasBuilding=function(_,index) assert(index==h.buildingIndex);return h.buildingPresent end,
            IsPillaged=function() return h.buildingPillaged end,
            GetNumGreatWorkSlots=function() return h.slotCount end,
            GetGreatWorkSlotType=function(_,index,slot)
              assert(index==h.buildingIndex and slot>=0 and slot<h.slotCount)
              return h.slotTypes[slot+1]=='GREATWORKSLOT_ARTIFACT' and 0 or 1
            end,
            GetGreatWorkInSlot=function(_,index,slot)
              assert(index==h.buildingIndex and slot>=0 and slot<h.slotCount)
              h.slotReads=h.slotReads+1
              if h.onSlot then h.onSlot(h.slotReads) end
              return h.slotWorks[slot+1]
            end}
          local city={GetID=function() return h.cityID or 66 end,GetOwner=function() return h.cityOwner end,
            GetX=function() return h.cityX end,GetY=function() return h.cityY end,
            GetBuildings=function() return buildings end}
          H.player={GetUnits=function() return {FindID=function(_,id)
              h.finds=h.finds+1;if h.onFind then h.onFind(h.finds) end
              assert(id==4);return unit
            end} end,
            GetCities=function() return {FindID=function(_,id) if id==66 then return city end end} end}
          GameInfo={Units=setmetatable({},{__index=function(_,key) if key==19 then return {UnitType=h.unitType} end end}),
            Buildings=setmetatable({},{__index=function(_,key)
              if key=='BUILDING_ARCHAEOLOGICAL_MUSEUM' then
                return {BuildingType=h.buildingType or key,Index=h.buildingIndex}
              end
            end}),GreatWorkSlotTypes={[0]={GreatWorkSlotType='GREATWORKSLOT_ARTIFACT'},
              [1]={GreatWorkSlotType='GREATWORKSLOT_WRITING'}}}
          H.unit=unit;H.city=city;H.buildings=buildings
        ''')
        self.lua.execute((ROOT / 'mod/Baiqi/Lua/BaiqiArchaeologyHome.lua').read_text(encoding='utf-8'))
        self.h = self.lua.globals().H
        self.read = self.lua.globals().BaiqiArchaeologyHome.Read

    def result(self):
        return self.read(self.h.player, self.h.pid, 4)

    def unavailable(self):
        value, status = self.result()
        self.assertIsNone(value)
        self.assertEqual(status, 'unavailable')

    def test_ten_exact_contract_data_cases(self):
        cases = json.loads((ROOT / 'tests/fixtures/archaeology_home_cases.json').read_text(encoding='utf-8'))
        for case in cases:
            with self.subTest(case=case['name']):
                self.setUp()
                for key, value in case['overrides'].items():
                    self.h[key] = self.lua.table_from(value) if isinstance(value, list) else value
                result, status = self.result()
                self.assertEqual(status, case['expectedStatus'])
                if status == 'ok':
                    self.assertEqual(list(result.emptySlots.values()), case['expectedEmptySlots'])
                    self.assertEqual(list(result.workIndices.values()), case['expectedWorkIndices'])
                else:
                    self.assertIsNone(result)

    def test_positive_uses_ui_binding_and_returns_only_plain_scalars(self):
        result, status = self.result()
        self.assertEqual(status, 'ok')
        self.assertEqual((result.unitID, result.homeCityID, result.cityX, result.cityY,
                          result.buildingIndex, result.slotCount), (4, 66, 2, 3, 10, 3))
        self.assertEqual(self.h.slotReads, 6)
        self.assertEqual(self.h.finds, 3)
        self.assertTrue(self.lua.eval('function(value) return getmetatable(value)==nil and getmetatable(value.emptySlots)==nil and getmetatable(value.workIndices)==nil end')(result))

    def test_changed_home_after_inventory_fails(self):
        self.lua.execute('H.onSlot=function(n) if n==3 then H.homeCityID=67 end end')
        self.unavailable()

    def test_same_work_set_in_different_slots_is_changed_inventory(self):
        self.lua.execute('H.onSlot=function(n) if n==3 then H.slotWorks={101,-1,-1} end end')
        self.unavailable()

    def test_changed_building_identity_and_final_unit_owner_fail(self):
        for script in (
            'H.onSlot=function(n) if n==3 then H.buildingIndex=11 end end',
            'H.onFind=function(n) if n==3 then H.unitOwner=8 end end',
        ):
            with self.subTest(script=script):
                self.setUp()
                self.lua.execute(script)
                self.unavailable()

    def test_unreadable_inventory_does_not_become_empty(self):
        self.lua.execute("H.buildings.GetGreatWorkInSlot=function() error('read unavailable') end")
        self.unavailable()

    def test_unknown_negative_nonfinite_and_boolean_work_ids_fail(self):
        for value in (-2, float('nan'), float('inf'), True):
            with self.subTest(value=value):
                self.setUp()
                self.h.slotWorks[1] = value
                self.unavailable()

    def test_maximum_slots_valid_and_duplicate_occupied_id_invalid(self):
        self.h.slotCount = 64
        self.h.slotWorks = self.lua.table_from(list(range(64)))
        self.h.slotTypes = self.lua.table_from(['GREATWORKSLOT_ARTIFACT'] * 64)
        result, status = self.result()
        self.assertEqual((status, result.slotCount, len(result.workIndices)), ('ok', 64, 64))
        self.assertEqual(self.h.slotReads, 128)
        self.h.slotWorks[64] = 0
        self.unavailable()

    def test_bad_ids_recycled_lookup_and_non_numeric_unit_type_fail(self):
        for field, value in (('pid', True), ('unitID', 5), ('homeCityID', -1),
                             ('cityID', 67), ('badType', 'UNIT_ARCHAEOLOGIST')):
            with self.subTest(field=field):
                self.setUp()
                self.h[field] = value
                self.unavailable()

    def test_malformed_namespace_is_contained(self):
        self.lua.execute("GameInfo=setmetatable({},{__index=function() error('namespace unavailable') end})")
        self.unavailable()


if __name__ == '__main__':
    unittest.main()
