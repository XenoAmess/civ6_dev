from pathlib import Path
import unittest
from lupa.lua53 import LuaRuntime
from lupa.lua51 import LuaRuntime as Lua51

ROOT=Path(__file__).resolve().parents[1]


class BuilderRoutePhaseTests(unittest.TestCase):
    runtime = staticmethod(LuaRuntime)

    def setUp(self):
        self.lua=getattr(self,'runtime',LuaRuntime)(unpack_returned_tuples=True)
        for name in ('tests/lua/mock_world.lua','tests/lua/mock_movement.lua',
                     'tests/lua/mock_path_ranking.lua','mod/Baiqi/Lua/BaiqiConfig.lua',
                     'mod/Baiqi/Lua/BaiqiPolicy.lua','mod/Baiqi/Lua/BaiqiPlanner.lua'):
            self.lua.execute((ROOT/name).read_text(encoding='utf-8'))
        self.lua.execute('''
local w=TestWorld
w.withBuilder=true;w.withSettler=false;w.queueSize=1
w.builderRecommendations={43};w.routeMoves=2;w.clock=0;w.validationCharged=false
w.objects.builder.GetMovesRemaining=function() return w.routeMoves end
Automation={GetTime=function() return w.clock end}
local path=UnitManager.GetMoveToPathEx
UnitManager.GetMoveToPathEx=function(...)
 local result=path(...);w.clock=w.clock+.010;return result
end
local units=Units.GetUnitsInPlot
Units.GetUnitsInPlot=function(...)
 local result=units(...)
 if #w.pathQueries>0 and not w.validationCharged then w.validationCharged=true;w.clock=w.clock+.010 end
 return result
end
''')
        self.private=self.lua.execute((ROOT/'mod/Baiqi/Lua/BaiqiController.lua').read_text(encoding='utf-8')
            +'\nreturn {Searches=function() return builderSearches end,Pending=function() return pendingUnits end}\n')
        self.w=self.lua.globals().TestWorld
        self.c=self.lua.globals().BaiqiController

    def moves(self):
        return [v for v in self.w.unitRequests.values() if v.op==10]

    def begin_query(self):
        self.c.RunNow()
        self.assertEqual(self.private.Searches()[3].phase,'query')
        self.assertEqual(len(self.w.pathQueries),0)
        self.assertEqual(self.moves(),[])

    def query_then_validate(self):
        self.begin_query()
        self.c.RunNow()
        self.assertEqual(self.private.Searches()[3].phase,'validate')
        self.assertEqual(len(self.w.pathQueries),1)
        self.assertEqual(self.moves(),[])
        self.c.RunNow()
        self.assertEqual(self.private.Searches()[3].phase,'write')
        self.assertEqual(self.moves(),[])

    def test_three_real_work_phases_submit_one_move_without_requery_or_replay(self):
        self.query_then_validate()
        self.c.RunNow()
        self.assertEqual(len(self.moves()),1)
        self.assertEqual((self.moves()[0].unit,self.moves()[0].params[14],self.moves()[0].params[15]),(3,3,3))
        self.assertIsNone(self.private.Searches()[3])
        self.assertIsNotNone(self.private.Pending()[3])
        self.c.RunNow();self.c.RunNow()
        self.assertEqual((len(self.moves()),len(self.w.pathQueries)),(1,1))
        self.assertTrue(all(r.unit==3 for r in self.w.unitRequests.values()))

    def test_missing_clock_keeps_synchronous_path_behavior(self):
        self.lua.execute('Automation=nil')
        self.c.RunNow()
        self.assertEqual((len(self.moves()),len(self.w.pathQueries)),(1,1))

    def test_escort_interrupt_cancels_packet_without_any_unit_order(self):
        self.begin_query()
        self.c.RunNow()
        self.w.formation=2
        self.c.RunNow()
        self.assertIsNone(self.private.Searches()[3])
        self.assertEqual((len(self.w.unitRequests),len(self.w.pathQueries)),(0,1))

    def test_moves_change_discards_old_packet_and_replans_with_fresh_key(self):
        self.begin_query()
        self.c.RunNow()
        old=self.private.Searches()[3].packet.key
        self.w.routeMoves=1
        self.c.RunNow()
        self.assertEqual(self.moves(),[])
        self.assertNotEqual(self.private.Searches()[3].key,old)
        # The old packet is discarded immediately. Local-work reads can exhaust
        # this callback, so the fresh native query resumes on the next callback.
        self.c.RunNow()
        self.assertNotEqual(self.private.Searches()[3].packet.key,old)
        self.assertEqual(len(self.w.pathQueries),2)

    def test_enemy_appearing_between_query_and_validation_prevents_move(self):
        self.begin_query()
        self.c.RunNow()
        self.w.enemyPlot=43
        self.c.RunNow()
        self.assertEqual(self.moves(),[])
        self.assertEqual(len(self.w.pathQueries),1)
        self.assertTrue(all(r.unit==3 for r in self.w.unitRequests.values()))

    def test_final_native_qualification_still_rechecks_current_threat(self):
        self.query_then_validate()
        self.lua.execute('''
local original=UnitManager.CanStartOperation
UnitManager.CanStartOperation=function(unit,op,...)
 local result=original(unit,op,...)
 if op==10 then TestWorld.enemyPlot=43 end
 return result
end
''')
        self.c.RunNow()
        self.assertEqual(self.moves(),[])
        self.assertEqual(len(self.w.pathQueries),1)

    def test_new_nearer_hint_before_write_restarts_query_in_current_priority(self):
        self.w.builderRecommendations=self.lua.table_from([45])
        self.query_then_validate()
        self.w.builderRecommendations=self.lua.table_from([45,43])
        self.c.RunNow()
        self.assertEqual(self.moves(),[])
        self.assertEqual(self.private.Searches()[3].phase,'query')
        self.c.RunNow()
        self.assertEqual(self.w.pathQueries[2].target,43)
        self.assertEqual(self.moves(),[])

    def test_city_production_is_not_starved_by_pending_over_budget_routes(self):
        self.lua.execute('Automation.GetTime=function() TestWorld.clock=TestWorld.clock+.010;return TestWorld.clock end')
        self.c.RunNow()
        self.assertEqual(self.private.Searches()[3].phase,'query')
        self.w.queueSize=0
        self.c.RunNow();self.c.RunNow();self.c.RunNow()
        self.assertEqual(len(self.w.cityRequests),1)
        self.assertEqual(self.moves(),[])

    def test_clock_failure_with_pending_packet_finishes_safely_once(self):
        self.query_then_validate()
        self.lua.execute('Automation=nil')
        self.c.RunNow()
        self.assertEqual(len(self.moves()),1)
        self.c.RunNow()
        self.assertEqual((len(self.moves()),len(self.w.pathQueries)),(1,1))

    def test_new_turn_clears_unsubmitted_proposal(self):
        self.begin_query()
        self.assertIsNotNone(self.private.Searches()[3])
        self.w.turn+=1
        self.c.RunNow(False)
        self.assertIsNone(self.private.Searches()[3])
        self.assertEqual((len(self.moves()),len(self.w.pathQueries)),(0,0))

    def test_pending_operation_cancels_unsubmitted_route_without_replay(self):
        self.query_then_validate()
        self.lua.globals().PrivatePending=self.private.Pending()
        self.lua.execute("PrivatePending[3]={id='existing',kind='MOVE_TO',from=42,moves=2,elapsed=0}")
        self.c.RunNow()
        self.assertEqual((len(self.moves()),len(self.w.pathQueries)),(0,1))
        # The two-continuation fairness boundary can postpone stale-search
        # retirement by one callback; it must never dispatch while pending.
        self.c.RunNow()
        self.assertIsNone(self.private.Searches()[3])
        self.assertIsNotNone(self.private.Pending()[3])
        self.assertEqual((len(self.moves()),len(self.w.pathQueries)),(0,1))

    def test_final_qualification_cannot_change_unit_or_core_authority(self):
        changes=('TestWorld.formation=2','TestWorld.busy=true',
                 'TestWorld.objects.builder.GetOwner=function() return 8 end',
                 'TestWorld.objects.builder.GetUnitType=function() return 0 end')
        for change in changes:
            with self.subTest(change=change):
                self.setUp()
                self.query_then_validate()
                self.lua.execute('''
local original=UnitManager.CanStartOperation
UnitManager.CanStartOperation=function(unit,op,...)
 local result=original(unit,op,...)
 if op==10 then CHANGE end
 return result
end
'''.replace('CHANGE',change))
                self.c.RunNow()
                self.assertEqual(len(self.w.unitRequests),0)
                self.assertEqual(len(self.w.pathQueries),1)

    def test_first_callback_scans_hints_once_without_native_path(self):
        self.lua.execute('''
local getAI=TestWorld.objects.city.GetCityAI
TestWorld.hintReads=0
TestWorld.objects.city.GetCityAI=function(...)
 local ai=getAI(...);local get=ai.GetImprovementRecommendationsForBuilder
 ai.GetImprovementRecommendationsForBuilder=function(...)
  TestWorld.hintReads=TestWorld.hintReads+1;return get(...)
 end
 return ai
end
''')
        self.begin_query()
        self.assertEqual(self.w.hintReads,1)
        self.c.RunNow()
        self.assertEqual((self.w.hintReads,len(self.w.pathQueries)),(2,1))

    def test_deferred_query_reads_new_nearest_hint_instead_of_old_target(self):
        self.w.builderRecommendations=self.lua.table_from([45])
        self.begin_query()
        self.w.builderRecommendations=self.lua.table_from([45,43])
        self.c.RunNow()
        self.assertEqual(self.w.pathQueries[1].target,43)
        self.assertEqual(self.moves(),[])

    def test_deferred_query_cannot_act_after_ownership_formation_or_idle_changes(self):
        for change in ('TestWorld.formation=2','TestWorld.busy=true',
                       'TestWorld.objects.builder.GetOwner=function() return 8 end',
                       'TestWorld.objects.builder.GetUnitType=function() return 0 end',
                       'TestWorld.withBuilder=false'):
            with self.subTest(change=change):
                self.setUp()
                self.begin_query()
                self.lua.execute(change)
                self.c.RunNow()
                self.assertEqual((len(self.w.pathQueries),len(self.w.unitRequests)),(0,0))

    def test_pending_operation_before_deferred_query_prevents_native_path(self):
        self.begin_query()
        self.lua.globals().PrivatePending=self.private.Pending()
        self.lua.execute("PrivatePending[3]={id='existing',kind='MOVE_TO',from=42,moves=2,elapsed=0}")
        self.c.RunNow()
        self.assertIsNone(self.private.Searches()[3])
        self.assertEqual((len(self.w.pathQueries),len(self.w.unitRequests)),(0,0))


class BuilderRoutePhaseLua51Tests(BuilderRoutePhaseTests):
    runtime = staticmethod(Lua51)
