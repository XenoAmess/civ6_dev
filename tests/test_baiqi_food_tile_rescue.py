"""Food rescue must preserve donor work and hold uncertain submissions."""
from pathlib import Path
import unittest
from lupa.lua51 import LuaRuntime

ROOT = Path(__file__).resolve().parents[1]


class FoodTileRescueTests(unittest.TestCase):
    def world(self):
        lua = LuaRuntime(unpack_returned_tuples=True)
        lua.execute((ROOT / 'tests/fixtures/food_tile_rescue.lua').read_text(encoding='utf-8'))
        for name in ('BaiqiFoodTileRescue', 'BaiqiFoodTileRescueRunner'):
            lua.execute((ROOT / f'mod/Baiqi/Lua/{name}.lua').read_text(encoding='utf-8'))
        lua.execute('''
          Game=E.Game;GameConfiguration=E.GameConfiguration;Players=E.Players
          PlayerConfigurations=E.PlayerConfigurations;Map={}
          for k,v in pairs(E.Map)do Map[k]=v end
          Map.GetCityPlots=nil -- actual Core has no UI purchase collection port
          BaiqiConfig={leader='LEADER_BAIQI',foodTileRescueIntentKey='FOOD_TEST_V1'}
          ExposedMembers={};E.ExposedMembers=ExposedMembers;W.props={}
          function CopyProperty(v)
            if type(v)~='table'then return v end
            local out={};for k,x in pairs(v)do out[k]=CopyProperty(x)end;return out
          end
          Players[0].GetProperty=function(_,key)
            if W.readError then error('unknown property')end
            return CopyProperty(W.props[key])
          end
          Players[0].SetProperty=function(_,key,value)
            W.propertyWrites=(W.propertyWrites or 0)+1
            W.props[key]=CopyProperty(value)
            if W.afterPersist then W.afterPersist(value)end
            if W.persistThrows then error('unknown after property mutation')end
          end
          Cities={GetPlotPurchaseCity=function(plot)
            local id=W.transferred and 458758 or 65536
            return Players[0]:GetCities():FindID(id)
          end}
        ''')
        for name in ('BaiqiFoodTileJournal', 'BaiqiFoodTileIntentGameplay'):
            lua.execute((ROOT / f'mod/Baiqi/Lua/{name}.lua').read_text(encoding='utf-8'))
        return lua

    def test_actual_shape_sparse_native_keys_submit_expected_source_plot_once(self):
        l = self.world()
        l.execute('''BaiqiFoodTileRescueRunner.Run(E,0)
          assert(#W.requests==1 and W.requests[1].city==458758)
          assert(not W.transferred and W.surplus==-1)
          for i=1,5 do W.turn=W.turn+1;BaiqiFoodTileRescueRunner.Run(E,0)end
          assert(#W.requests==1)''')

    def test_false_void_throw_and_reentry_hold_without_native_effect(self):
        for mode in ('W.requestReturn=false', 'W.requestReturn=nil', 'W.throw=true', 'W.reenter=true'):
            with self.subTest(mode=mode):
                l = self.world()
                l.execute(mode + ''';BaiqiFoodTileRescueRunner.Run(E,0)
                  W.turn=209;BaiqiFoodTileRescueRunner.Run(E,0)
                  assert(#W.requests==1 and W.surplus==-1)''')

    def test_observed_assignment_and_real_nonnegative_food_clear_hold_without_repeat(self):
        l = self.world()
        l.execute('''W.apply=true;BaiqiFoodTileRescueRunner.Run(E,0)
          W.turn=209;BaiqiFoodTileRescueRunner.Run(E,0)
          assert(#W.requests==1 and W.transferred and W.surplus==0)''')

    def test_donor_work_and_uncertain_or_unsafe_inputs_never_submit(self):
        cases = ['W.sourceDistance=3', 'W.sourceHasPlot=true', 'W.visible=false',
                 'W.revealed=false', 'W.manageError=true', 'W.allowed=false',
                 'W.targetLocked=2', 'W.starvation=-1', 'W.favored=false',
                 'W.disfavored=true', 'W.surplus=0', 'W.surplus=-2',
                 'W.busy=true', 'W.processing=true', 'W.human=false',
                 'W.active=false', 'W.multi=true', 'W.owner=1',
                 'W.leader="OTHER"', 'W.count=3', 'W.staleFind=true']
        for case in cases:
            with self.subTest(case=case):
                l = self.world()
                l.execute(case + ';BaiqiFoodTileRescueRunner.Run(E,0);assert(#W.requests==0)')

    def test_last_boundary_changes_are_rejected(self):
        for change in ['W.sourceDistance=3', 'W.sourceHasPlot=true', 'W.surplus=0',
                       'W.owner=1', 'W.busy=true', 'W.sourceID=999',
                       'E.CityManager.RequestCommand=function()error("foreign")end']:
            with self.subTest(change=change):
                l = self.world()
                l.execute('W.onPermission=function(n)if n==2 then ' + change + ''' end end
                  BaiqiFoodTileRescueRunner.Run(E,0);assert(#W.requests==0)''')

    def planner(self):
        l = self.world()
        l.execute('''S={player=0,owner=0,cityID=458758,population=8,surplus=-1,starvation=2,
          zeroFoodSpecialists=2,favored=true,disfavored=false,complete=true,mapWidth=74,mapHeight=46,
          targets={{plotID=2277,x=57,y=30,food=1,sourceCityID=65536,sourcePopulation=16,sourceSurplus=16,
            sourceManageHasPlot=false,sourceManageComplete=true,district=-1,improvement=-1,
            nativeAllowed=true,sourceDistance=4,targetDistance=3,owner=0,visible=true,revealed=true}}}''')
        return l

    def test_pure_plan_preserves_source_city_and_legitimate_sentinels(self):
        l = self.planner()
        l.execute('''local p=BaiqiFoodTileRescue.Plan(S)
          assert(p.cityID==458758 and p.sourceCityID==65536 and p.plotID==2277 and p.expectedSurplus==0)''')

    def test_planner_rejects_holes_metatables_nonfinite_and_bad_bounds(self):
        for change in ['S.targets[3]=S.targets[1]', 'S.targets[0]=S.targets[1]',
                       'S.targets.extra=true', 'S.targets[2]=S.targets[1]',
                       'setmetatable(S,{})', 'setmetatable(S.targets,{})',
                       'setmetatable(S.targets[1],{})', 'S.cityID=0/0',
                       'S.targets[1].sourceCityID=math.huge', 'S.targets[1].sourceLocked=0/0',
                       'S.targets[1].sourceWorked=0', 'S.targets[1].x=74',
                       'S.starvation=-1', 'S.population=0', 'S.zeroFoodSpecialists=0']:
            with self.subTest(change=change):
                l = self.planner()
                l.execute(change + ';assert(BaiqiFoodTileRescue.Plan(S)==nil)')

    def test_prediction_needs_enough_food_and_minimal_eligible_deterministic_choice(self):
        l = self.planner()
        l.execute('''local copy={};for k,v in pairs(S.targets[1])do copy[k]=v end
          copy.plotID=2276;copy.food=2;S.targets[2]=copy
          assert(BaiqiFoodTileRescue.Plan(S).plotID==2277)
          copy.food=1;assert(BaiqiFoodTileRescue.Plan(S).plotID==2276)
          S.surplus=-3;assert(BaiqiFoodTileRescue.Plan(S)==nil)''')

    def test_admin_supplies_original_native_ports_and_continues_other_administration(self):
        from tests.test_baiqi_food_focus import FoodFocusConsumerTests
        fixture = FoodFocusConsumerTests(methodName='runTest')
        fixture.setUp()
        fixture.lua.execute('''Map={native=true};PlayersVisibility={};CityCommandResults={}
          RescueCalls=0;BaiqiFoodTileRescueRunner={Run=function(e,pid)
            assert(e.Map==Map and e.PlayersVisibility==PlayersVisibility and e.UI==UI)
            assert(e.CityManager==CityManager and e.CityCommandResults==CityCommandResults)
            assert(e.CityCommandTypes==CityCommandTypes and e.YieldTypes==YieldTypes)
            assert(e.ExposedMembers==ExposedMembers)
            RescueCalls=RescueCalls+1
          end}''')
        fixture.run_admin(1)
        self.assertEqual(fixture.lua.globals().RescueCalls, 1)


if __name__ == '__main__':
    unittest.main()
