"""Real scheduler: public border screening must cover existing goals and writes."""
from pathlib import Path
import unittest

from lupa.lua53 import LuaRuntime

ROOT = Path(__file__).resolve().parents[1]


class SettlementBorderTests(unittest.TestCase):
    def setUp(self):
        self.lua = LuaRuntime(unpack_returned_tuples=True)
        for name in ('tests/lua/mock_world.lua', 'tests/lua/mock_movement.lua',
                     'tests/lua/mock_path_ranking.lua',
                     'tests/lua/mock_settlement_border.lua',
                     'mod/Baiqi/Lua/BaiqiConfig.lua',
                     'mod/Baiqi/Lua/BaiqiPolicy.lua',
                     'mod/Baiqi/Lua/BaiqiPlanner.lua',
                     'mod/Baiqi/Lua/BaiqiController.lua'):
            self.lua.execute((ROOT / name).read_text(encoding='utf-8'))
        self.w = self.lua.globals().TestWorld
        self.controller = self.lua.globals().BaiqiController

    def run_now(self, count=2):
        for _ in range(count):
            self.controller.RunNow()
        self.assertNotIn('脚本错误', self.controller.GetStatus())
        self.assertEqual(len(self.w.cityRequests), 0)
        for r in self.w.unitRequests.values():
            self.assertEqual(r.unit, 2, 'Only the civilian may receive background orders')

    def orders(self, op):
        return [r for r in self.w.unitRequests.values() if r.op == op]

    def test_known_foreign_border_without_owned_support_waits(self):
        self.run_now()
        self.assertEqual(self.orders(10), [])
        self.assertEqual(self.orders(11), [])

    def test_remote_island_without_visible_foreign_city_can_continue(self):
        self.w.foreign = False
        self.run_now()
        self.assertEqual(len(self.orders(10)), 1)

    def test_near_own_support_keeps_native_recommendation(self):
        self.w.ownX, self.w.ownY = 2, 3
        self.run_now()
        self.assertEqual(len(self.orders(10)), 1)

    def test_own_support_does_not_bypass_visible_foreign_minimum_city_distance(self):
        self.w.ownX, self.w.ownY = 2, 3
        self.w.nearForeign = True
        self.run_now()
        self.assertEqual(self.orders(10), [])

    def test_existing_owned_city_minimum_distance_is_preserved(self):
        self.w.ownX, self.w.ownY = 6, 4
        self.w.foreign = False
        self.run_now()
        self.assertEqual(self.orders(10), [])

    def test_capital_is_not_blocked_by_border_screen(self):
        self.w.withCity = False
        self.run_now(1)
        self.assertEqual(len(self.orders(11)), 1)

    def test_unrevealed_foreign_city_is_never_read(self):
        self.w.hidden[200] = True
        self.run_now()
        self.assertEqual(len(self.orders(10)), 1)
        self.assertEqual(self.w.cityQueries, 0)

    def test_fogged_foreign_city_is_never_read(self):
        self.w.fogged[200] = True
        self.run_now()
        self.assertEqual(len(self.orders(10)), 1)
        self.assertEqual(self.w.cityQueries, 0)

    def test_unknown_native_city_flag_does_not_mean_empty(self):
        self.w.unknownCityFlag = True
        self.run_now()
        self.assertEqual(self.orders(10), [])

    def test_missing_native_city_object_does_not_mean_no_foreign_city(self):
        self.w.lookupMissing = True
        self.run_now()
        self.assertEqual(self.orders(10), [])

    def test_native_city_lookup_error_waits_without_stopping_controller(self):
        self.w.lookupThrows = True
        self.run_now()
        self.assertEqual(self.orders(10), [])

    def test_wrong_native_city_coordinates_wait(self):
        self.w.wrongCityCoordinates = True
        self.run_now()
        self.assertEqual(self.orders(10), [])

    def test_invalid_native_city_identity_waits(self):
        self.w.badCityID = True
        self.run_now()
        self.assertEqual(self.orders(10), [])

    def test_changed_native_geometry_object_waits(self):
        self.w.badNeighbor = True
        self.run_now()
        self.assertEqual(self.orders(10), [])

    def test_positive_city_count_with_empty_inventory_is_unknown(self):
        self.w.emptyOwnInventory = True
        self.w.foreign = False
        self.run_now()
        self.assertEqual(self.orders(10), [])

    def test_unknown_owned_city_distance_is_not_safe(self):
        self.w.foreign = False
        self.lua.execute('''
            local old=Map.GetPlotDistance
            Map.GetPlotDistance=function(x,y,x2,y2)
              if (x==0 and y==0)or(x2==0 and y2==0)then return 0/0 end
              return old(x,y,x2,y2)
            end
        ''')
        self.run_now()
        self.assertEqual(self.orders(10), [])

    def select_goal_then_arrive(self):
        self.w.foreign = False
        self.run_now(1)
        self.assertEqual(len(self.orders(10)), 1)
        self.w.turn += 1
        self.w.settlerPlot = 47
        self.w.foreign = True

    def test_old_goal_cannot_found_after_foreign_city_appears(self):
        self.select_goal_then_arrive()
        self.run_now()
        self.assertEqual(self.orders(11), [])

    def test_old_goal_can_try_another_native_recommendation(self):
        self.select_goal_then_arrive()
        self.w.settlementRecommendations = self.lua.table_from([47, 46])
        # Original 46 is also in range; add a separately qualified remote site.
        self.lua.execute('''
            local w=TestWorld;local old=Map.GetPlotByIndex;local xy=Map.GetPlot
            local plots={}
            for i,y in pairs({[250]=10,[251]=6,[252]=7,[253]=8,[254]=9})do
              local id,py=i,y
              plots[id]={GetIndex=function()return id end,GetX=function()return 2 end,
                GetY=function()return py end,GetOwner=function()return -1 end,
                GetFeatureType=function()return -1 end,IsWater=function()return false end,
                IsImpassable=function()return false end,IsCity=function()return false end}
            end
            Map.GetPlotByIndex=function(i)return plots[i]or old(i)end
            Map.GetPlot=function(x,y)
              for _,p in pairs(plots)do if x==2 and y==p:GetY()then return p end end
              return xy(x,y)
            end
            w.settlementRecommendations={47,250}
            w.paths[250]={47,74,73,72,71,70,44,45,251,252,253,254,250}
        ''')
        self.run_now()
        self.assertEqual(self.orders(11), [])
        self.assertGreater(len(self.orders(10)), 1)

    def test_foreign_city_appearing_during_found_qualification_blocks_write(self):
        self.select_goal_then_arrive()
        self.w.foreign = False
        self.lua.execute('''
            local old=UnitManager.CanStartOperation;local n=0
            UnitManager.CanStartOperation=function(u,op,...)
              local ok=old(u,op,...)
              if op==11 then n=n+1;if n==2 then TestWorld.foreign=true end end
              return ok
            end
        ''')
        self.run_now()
        self.assertEqual(self.orders(11), [])

    def test_unknown_visibility_does_not_mean_no_foreign_city(self):
        self.lua.execute('''
            local old=PlayersVisibility[7].IsVisible
            PlayersVisibility[7].IsVisible=function(self,x,y)
              if x==12 and y==4 then return nil end;return old(self,x,y)
            end
        ''')
        self.run_now()
        self.assertEqual(self.orders(10), [])
        self.assertEqual(self.w.cityQueries, 0)

    def test_unknown_revelation_does_not_mean_clear_neighborhood(self):
        self.lua.execute('''
            local old=PlayersVisibility[7].IsRevealed
            PlayersVisibility[7].IsRevealed=function(self,x,y)
              if x==12 and y==4 then return nil end;return old(self,x,y)
            end
        ''')
        self.run_now()
        self.assertEqual(self.orders(10), [])
        self.assertEqual(self.w.cityQueries, 0)

    def test_owned_support_lost_during_found_qualification_blocks_write(self):
        self.w.foreign = False
        self.w.ownX, self.w.ownY = 2, 3
        self.run_now(1)
        self.w.turn += 1
        self.w.settlerPlot = 47
        self.w.foreign = True
        self.lua.execute('''
            local old=UnitManager.CanStartOperation;local n=0
            UnitManager.CanStartOperation=function(u,op,...)
              local ok=old(u,op,...)
              if op==11 then n=n+1;if n==2 then TestWorld.ownX=0;TestWorld.ownY=0 end end
              return ok
            end
        ''')
        self.run_now()
        self.assertEqual(self.orders(11), [])


if __name__ == '__main__':
    unittest.main()
