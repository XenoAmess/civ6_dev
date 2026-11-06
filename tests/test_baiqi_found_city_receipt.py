"""Consumed settlers need a new city effect; disappearance is not a receipt."""
from pathlib import Path
import unittest

from lupa.lua53 import LuaRuntime

ROOT = Path(__file__).resolve().parents[1]


class FoundCityReceiptTests(unittest.TestCase):
    def setUp(self):
        self.lua = LuaRuntime(unpack_returned_tuples=True)
        for name in ('tests/lua/mock_world.lua', 'tests/lua/mock_movement.lua',
                     'tests/lua/mock_path_ranking.lua',
                     'mod/Baiqi/Lua/BaiqiConfig.lua',
                     'mod/Baiqi/Lua/BaiqiPolicy.lua',
                     'mod/Baiqi/Lua/BaiqiPlanner.lua'):
            self.lua.execute((ROOT / name).read_text(encoding='utf-8'))
        self.lua.execute('''
            local w=TestWorld;local o=w.objects
            w.withSettler=true;w.withBuilder=false;w.withCity=false;w.queueSize=1
            w.logs={};print=function(...)
              local a={};for i=1,select('#',...)do a[i]=tostring(select(i,...))end
              w.logs[#w.logs+1]=table.concat(a,'\t')
            end
            local city=setmetatable({GetID=function()return w.effectCityID or 366 end,
              GetOwner=function()return w.effectOwner or 7 end,
              GetX=function()return w.effectX or 2 end,
              GetY=function()return 3 end},{__index=o.city})
            w.effectCity=city
            Map.GetPlotByIndex(42).IsCity=function()
              if w.unknownIsCity then return nil end
              return w.cityEffect==true
            end
            CityManager.GetCityAt=function(x,y)
              w.cityLookups=(w.cityLookups or 0)+1
              if w.lookupThrows then error('native lookup unavailable')end
              if w.cityEffect then return city end
            end
            local function members(list)return function()local i=0;return function()
              i=i+1;if list[i]then return i,list[i]end end end end
            o.player.GetCities=function()
              local list={};if w.cityEffect and(w.effectOwner or 7)==7 then list={city}end
              return{Members=members(list),GetCount=function()return #list end,
                FindID=function(_,id)
                  if w.cityAlias then return o.city end
                  for _,c in ipairs(list)do if c:GetID()==id then return c end end
                end}
            end
            local units=o.player.GetUnits
            o.player.GetUnits=function(...)
              local collection=units(...);local find=collection.FindID
              collection.FindID=function(_,id)
                if id==2 and w.unitAlias then return o.army end
                if id==2 and w.lookupMissing then return nil end
                return find(collection,id)
              end
              return collection
            end
            o.settler.GetMovesRemaining=function()return w.actorMoves or 2 end
        ''')
        self.lua.execute((ROOT / 'mod/Baiqi/Lua/BaiqiController.lua').read_text(encoding='utf-8'))
        self.w = self.lua.globals().TestWorld
        self.controller = self.lua.globals().BaiqiController

    def run_now(self, count=1):
        for _ in range(count):
            self.controller.RunNow()
        self.assertNotIn('脚本错误', self.controller.GetStatus())
        for r in self.w.unitRequests.values():
            self.assertEqual(r.unit, 2, 'Only the settler receives background commands')

    def found_count(self):
        return sum(r.op == 11 for r in self.w.unitRequests.values())

    def observed(self):
        return [x for x in self.w.logs.values()
                if 'BAIQI|observed|' in x and '|kind=FOUND_CITY' in x]

    def issue(self):
        self.run_now()
        self.assertEqual(self.found_count(), 1)

    def effect(self):
        self.w.withSettler = False
        self.w.cityEffect = True

    def test_consumed_settler_and_new_owned_city_get_one_receipt(self):
        self.issue()
        self.effect()
        self.run_now(4)
        self.assertEqual(len(self.observed()), 1)
        self.assertEqual(self.found_count(), 1)

    def test_missing_unit_waits_for_late_city_across_turns(self):
        self.issue()
        self.w.withSettler = False
        self.run_now(3)
        self.w.turn += 1
        self.run_now()
        self.assertEqual(self.observed(), [])
        self.w.cityEffect = True
        self.run_now(2)
        self.assertEqual(len(self.observed()), 1)
        self.assertEqual(self.found_count(), 1)

    def test_missing_unit_without_city_never_claims_success(self):
        self.issue()
        self.w.withSettler = False
        self.w.turn += 2
        self.run_now(4)
        self.assertEqual(self.observed(), [])
        self.assertEqual(self.found_count(), 1)

    def test_changed_moves_do_not_prove_city_foundation_or_allow_replay(self):
        self.issue()
        self.w.actorMoves = 1
        self.run_now(2)
        self.w.turn += 1
        self.run_now(2)
        self.assertEqual(self.observed(), [])
        self.assertEqual(self.found_count(), 1)

    def test_live_settler_and_city_do_not_prove_consumption(self):
        self.issue()
        self.w.cityEffect = True
        self.run_now(3)
        self.assertEqual(self.observed(), [])
        self.w.withSettler = False
        self.run_now()
        self.assertEqual(len(self.observed()), 1)

    def test_full_unit_id_alias_is_unknown_until_lookup_recovers(self):
        self.issue()
        self.effect()
        self.w.unitAlias = True
        self.run_now(2)
        self.assertEqual(self.observed(), [])
        self.w.unitAlias = False
        self.run_now()
        self.assertEqual(len(self.observed()), 1)

    def test_lookup_missing_with_actor_in_inventory_is_not_consumed(self):
        self.issue()
        self.w.cityEffect = True
        self.w.lookupMissing = True
        self.run_now(2)
        self.assertEqual(self.observed(), [])
        self.w.withSettler = False
        self.run_now()
        self.assertEqual(len(self.observed()), 1)

    def test_foreign_city_is_not_a_success_receipt(self):
        self.issue()
        self.effect()
        self.w.effectOwner = 8
        self.w.siteOwners[42] = 8
        self.run_now(3)
        self.assertEqual(self.observed(), [])

    def test_city_id_alias_is_not_a_success_receipt(self):
        self.issue()
        self.effect()
        self.w.cityAlias = True
        self.run_now(3)
        self.assertEqual(self.observed(), [])

    def test_city_at_wrong_coordinates_is_not_a_success_receipt(self):
        self.issue()
        self.effect()
        self.w.effectX = 3
        self.run_now(3)
        self.assertEqual(self.observed(), [])

    def test_unknown_city_id_is_not_a_success_receipt(self):
        self.issue()
        self.effect()
        self.w.effectCityID = -1
        self.run_now(3)
        self.assertEqual(self.observed(), [])

    def test_native_lookup_error_waits_and_recovers_without_replay(self):
        self.issue()
        self.effect()
        self.w.lookupThrows = True
        self.run_now(2)
        self.assertEqual(self.observed(), [])
        self.w.lookupThrows = False
        self.run_now()
        self.assertEqual(len(self.observed()), 1)
        self.assertEqual(self.found_count(), 1)

    def test_city_appearing_during_native_qualification_blocks_dispatch(self):
        self.lua.execute('''
            local old=UnitManager.CanStartOperation;local n=0
            UnitManager.CanStartOperation=function(u,op,...)
              local ok=old(u,op,...)
              if op==11 then n=n+1;if n==2 then TestWorld.cityEffect=true end end
              return ok
            end
        ''')
        self.run_now(2)
        self.assertEqual(self.found_count(), 0)
        self.assertEqual(self.observed(), [])

    def test_unknown_native_empty_city_fact_blocks_dispatch(self):
        self.w.unknownIsCity = True
        self.run_now(2)
        self.assertEqual(self.found_count(), 0)

    def test_hidden_target_never_queries_city_for_receipt(self):
        self.issue()
        self.effect()
        self.w.fogged[42] = True
        before = self.w.cityLookups
        self.run_now(2)
        self.assertEqual(self.w.cityLookups, before)
        self.assertEqual(self.observed(), [])

    def test_city_lookup_unavailable_before_write_blocks_dispatch(self):
        self.w.lookupThrows = True
        self.run_now(2)
        self.assertEqual(self.found_count(), 0)

    def test_escort_created_by_empty_site_lookup_blocks_dispatch(self):
        self.lua.execute('''
            local old=CityManager.GetCityAt
            CityManager.GetCityAt=function(...)
              local city=old(...);TestWorld.formation=2;return city
            end
        ''')
        self.run_now(2)
        self.assertEqual(self.found_count(), 0)

    def test_unit_moved_by_empty_site_lookup_blocks_dispatch(self):
        self.lua.execute('''
            local old=CityManager.GetCityAt
            CityManager.GetCityAt=function(...)
              local city=old(...);TestWorld.settlerPlot=43;return city
            end
        ''')
        self.run_now()
        self.assertEqual(self.found_count(), 0)

    def test_player_changed_by_empty_site_lookup_blocks_dispatch(self):
        self.lua.execute('''
            local old=CityManager.GetCityAt
            CityManager.GetCityAt=function(...)
              local city=old(...);Game.GetLocalPlayer=function()return 8 end;return city
            end
        ''')
        self.run_now()
        self.assertEqual(self.found_count(), 0)

    def test_unknown_native_city_flag_waits_then_recovers(self):
        self.issue()
        self.effect()
        self.w.unknownIsCity = True
        self.run_now(2)
        self.assertEqual(self.observed(), [])
        self.w.unknownIsCity = False
        self.run_now()
        self.assertEqual(len(self.observed()), 1)

    def test_city_lookup_and_native_plot_must_agree(self):
        self.issue()
        self.effect()
        self.lua.execute('Map.GetPlotByIndex(42).IsCity=function()return false end')
        self.run_now(3)
        self.assertEqual(self.observed(), [])

    def test_unknown_owned_unit_inventory_metadata_is_not_consumption(self):
        self.issue()
        self.effect()
        self.lua.execute('TestWorld.objects.army.GetID=function()return nil end')
        self.run_now(3)
        self.assertEqual(self.observed(), [])

    def test_foreign_city_then_capture_cannot_relabel_original_found(self):
        self.issue()
        self.effect()
        self.w.effectOwner = 8
        self.w.siteOwners[42] = 8
        self.run_now()
        self.w.effectOwner = 7
        self.w.siteOwners[42] = 7
        self.run_now(3)
        self.assertEqual(self.observed(), [])

    def test_site_becomes_foreign_during_native_qualification_blocks_dispatch(self):
        self.lua.execute('''
            local old=UnitManager.CanStartOperation;local n=0
            UnitManager.CanStartOperation=function(u,op,...)
              local ok=old(u,op,...)
              if op==11 then n=n+1;if n==2 then TestWorld.siteOwners[42]=8 end end
              return ok
            end
        ''')
        self.run_now(2)
        self.assertEqual(self.found_count(), 0)


if __name__ == '__main__':
    unittest.main()
