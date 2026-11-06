"""Real scheduler counterexample: a single site needs a different first step."""
from pathlib import Path
import unittest

from lupa.lua53 import LuaRuntime

ROOT = Path(__file__).resolve().parents[1]


class SettlerDetourTests(unittest.TestCase):
    def setUp(self):
        self.lua = LuaRuntime(unpack_returned_tuples=True)
        for name in ('tests/lua/mock_world.lua', 'tests/lua/mock_movement.lua',
                     'tests/lua/mock_path_ranking.lua',
                     'mod/Baiqi/Lua/BaiqiConfig.lua',
                     'mod/Baiqi/Lua/BaiqiPolicy.lua',
                     'mod/Baiqi/Lua/BaiqiPlanner.lua',
                     'mod/Baiqi/Lua/BaiqiController.lua'):
            self.lua.execute((ROOT / name).read_text(encoding='utf-8'))
        self.lua.execute('''
            local w=TestWorld;local o=w.objects
            w.withSettler=true;w.withBuilder=false;w.queueSize=1
            w.settlementRecommendations={47}
            w.paths[47]={42,43,70,71,72,73,74,47}
            GameInfo.Units[3]={UnitType='UNIT_GREAT_PROPHET',Index=3,
              FormationClass='FORMATION_CLASS_CIVILIAN',Maintenance=0}
            local prophet={GetID=function()return 5 end,GetOwner=function()return 7 end,
              GetUnitType=function()return 3 end,GetX=function()return 3 end,
              GetY=function()return 3 end,GetMovesRemaining=function()return 0 end,
              GetFormationUnitCount=function()return 1 end}
            o.prophet=prophet
            local original=Units.GetUnitsInPlot
            Units.GetUnitsInPlot=function(plot)
              if plot:GetIndex()==43 then return{prophet}end
              return original(plot)
            end
            local getUnits=o.player.GetUnits
            o.player.GetUnits=function(...)
              local list={};for _,u in getUnits(...):Members()do list[#list+1]=u end
              list[#list+1]=prophet
              return{Members=function()local i=0;return function()
                i=i+1;if list[i]then return i,list[i]end end end,
                FindID=function(_,id)for _,u in ipairs(list)do
                  if u:GetID()==id then return u end end end}
            end
        ''')
        self.w = self.lua.globals().TestWorld
        self.controller = self.lua.globals().BaiqiController

    def run_turn(self, count=3):
        for _ in range(count):
            self.controller.RunNow()
        self.assertNotIn('脚本错误', self.controller.GetStatus())
        self.assertEqual(len(self.w.cityRequests), 0)
        for r in self.w.unitRequests.values():
            self.assertEqual(r.unit, 2, 'Only the settler may receive an order')

    def moves(self):
        return [(r.params[14], r.params[15])
                for r in self.w.unitRequests.values() if r.op == 10]

    def test_only_site_uses_safe_detour_without_moving_prophet(self):
        self.run_turn()
        self.assertEqual(self.moves(), [(2, 4)])

    def test_unowned_water_detour_still_uses_native_permission(self):
        self.lua.execute('''
            TestWorld.siteOwners[44]=-1
            Map.GetPlotByIndex(44).IsWater=function()return true end
        ''')
        self.run_turn()
        self.assertEqual(self.moves(), [(2, 4)])

    def test_unavailable_direct_native_edge_waits(self):
        self.w.paths[44] = False
        self.run_turn()
        self.assertEqual(self.moves(), [])

    def test_foreign_detour_waits(self):
        self.w.siteOwners[44] = 8
        self.run_turn()
        self.assertEqual(self.moves(), [])

    def test_hidden_detour_never_reads_occupancy(self):
        self.w.hidden[44] = True
        self.lua.execute('''
            local old=Units.GetUnitsInPlot
            Units.GetUnitsInPlot=function(p)
              assert(p:GetIndex()~=44,'hidden occupancy queried');return old(p)
            end
        ''')
        self.run_turn()
        self.assertEqual(self.moves(), [])

    def test_explored_fogged_detour_never_reads_occupancy(self):
        self.w.fogged[44] = True
        self.run_turn()
        self.assertEqual(self.moves(), [])

    def test_escort_receives_no_detour_orders(self):
        self.w.formation = 2
        self.run_turn()
        self.assertEqual(len(self.w.unitRequests), 0)

    def test_native_move_rejection_keeps_waiting(self):
        self.w.rejectMoveX = 2
        self.run_turn()
        self.assertEqual(self.moves(), [])

    def test_occupied_detour_waits(self):
        self.lua.execute('''
            local old=Units.GetUnitsInPlot
            Units.GetUnitsInPlot=function(p)
              if p:GetIndex()==44 then return {TestWorld.objects.prophet}end
              return old(p)
            end
        ''')
        self.run_turn()
        self.assertEqual(self.moves(), [])

    def test_no_progress_neighbor_is_not_random_exploration(self):
        self.lua.execute('''
            local old=Map.GetPlotDistance
            Map.GetPlotDistance=function(x,y,x2,y2)
              if x==2 and y==4 and x2==8 and y2==4 then return 7 end
              return old(x,y,x2,y2)
            end
        ''')
        self.run_turn()
        self.assertEqual(self.moves(), [])

    def test_neighbor_without_original_route_rejoin_waits(self):
        self.lua.execute('TestWorld.paths[47]={42,43,60,61,62,48,47}')
        self.run_turn()
        self.assertEqual(self.moves(), [])

    def test_native_edge_with_wrong_origin_waits(self):
        self.lua.execute('TestWorld.paths[44]={43,44}')
        self.run_turn()
        self.assertEqual(self.moves(), [])

    def test_native_edge_requiring_intermediate_tile_waits(self):
        self.lua.execute('TestWorld.paths[44]={42,70,44}')
        self.run_turn()
        self.assertEqual(self.moves(), [])

    def test_unknown_native_permission_does_not_mean_allowed(self):
        self.lua.execute('''
            local old=UnitManager.CanStartOperation
            UnitManager.CanStartOperation=function(u,op,mode,params)
              if op==10 and params and params[14]==2 then return nil end
              return old(u,op,mode,params)
            end
        ''')
        self.run_turn()
        self.assertEqual(self.moves(), [])

    def test_unavailable_unit_layer_does_not_mean_empty(self):
        self.lua.execute('''
            local old=Units.GetUnitsInPlotLayerID
            Units.GetUnitsInPlotLayerID=function(p,layer)
              if p:GetIndex()==44 then return nil end
              return old(p,layer)
            end
        ''')
        self.run_turn()
        self.assertEqual(self.moves(), [])

    def test_unknown_occupant_type_does_not_mean_free_slot(self):
        self.lua.execute('''
            local old=Units.GetUnitsInPlot
            Units.GetUnitsInPlot=function(p)
              if p:GetIndex()==44 then return {{GetOwner=function()return 7 end,
                GetUnitType=function()return 999 end}}end
              return old(p)
            end
        ''')
        self.run_turn()
        self.assertEqual(self.moves(), [])

    def test_threat_created_by_detour_query_invalidates_whole_route(self):
        self.lua.execute('''
            local old=UnitManager.GetMoveToPathEx
            UnitManager.GetMoveToPathEx=function(u,index)
              local result=old(u,index)
              if index==44 then TestWorld.enemyPlot=74 end
              return result
            end
        ''')
        self.run_turn()
        self.assertEqual(self.moves(), [])

    def test_changed_target_ownership_invalidates_detour(self):
        self.lua.execute('''
            local old=UnitManager.GetMoveToPathEx
            UnitManager.GetMoveToPathEx=function(u,index)
              local result=old(u,index)
              if index==44 then TestWorld.siteOwners[47]=8 end
              return result
            end
        ''')
        self.run_turn()
        self.assertEqual(self.moves(), [])

    def test_nonadjacent_native_first_step_does_not_trigger_detour(self):
        self.lua.execute('TestWorld.paths[47]={42,60,70,71,72,73,74,47}')
        self.run_turn()
        self.assertEqual(self.moves(), [])

    def test_native_qualification_race_cannot_move_into_new_occupant(self):
        self.lua.execute('''
            local old=UnitManager.CanStartOperation
            UnitManager.CanStartOperation=function(u,op,mode,params)
              local ok=old(u,op,mode,params)
              if op==10 and params and params[14]==2 and params[15]==4 then
                local prior=Units.GetUnitsInPlot
                Units.GetUnitsInPlot=function(p)
                  if p:GetIndex()==44 then return {TestWorld.objects.prophet}end
                  return prior(p)
                end
              end
              return ok
            end
        ''')
        self.run_turn()
        self.assertEqual(self.moves(), [])


if __name__ == '__main__':
    unittest.main()
