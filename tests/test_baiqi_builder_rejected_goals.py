"""Actual Controller calls with movement and native planning replies supplied by fixtures."""
import unittest
import test_baiqi_path_ranking as ranking
import test_baiqi_builder_route_phases as phases


class BuilderRejectedGoalTests(unittest.TestCase):
    setUp = ranking.PathRankingTests.setUp

    def fixture(self, phased=False):
        self.lua.execute('''
local w=TestWorld
w.builderRecommendations={46,50};w.siteOwners[46]=7;w.siteOwners[50]=7
w.failAt43=true;w.moveCount=0;w.stopAfter=3;w.moveEdges={}
w.objects.builder.GetX=function() return Map.GetPlotByIndex(w.builderPlot):GetX() end
w.objects.builder.GetY=function() return Map.GetPlotByIndex(w.builderPlot):GetY() end
local request=UnitManager.RequestOperation
UnitManager.RequestOperation=function(unit,op,params,...)
 local from=w.builderPlot
 local result=request(unit,op,params,...)
 if op==10 then
  local plot=Map.GetPlot(params[14],params[15]);assert(plot)
  w.moveCount=w.moveCount+1
  w.moveEdges[#w.moveEdges+1]={from=from,to=plot:GetIndex(),unit=unit:GetID()}
  w.builderPlot=plot:GetIndex();w.builderMoves=w.builderMoves-.5
  if w.moveCount>=w.stopAfter then w.builderMoves=0 end
 end
 return result
end
UnitManager.GetMoveToPathEx=function(unit,index)
 local start=w.builderPlot
 w.pathQueries[#w.pathQueries+1]={unit=unit:GetID(),target=index,from=start}
 if w.busyOnQuery then w.busyOnQuery=false;w.busy=true;return nil end
 if index==46 then
  if start==42 then return {plots={42,43,60,61,62,48,46}} end
  if start==43 and not w.failAt43 then return {plots={43,60,61,62,48,46}} end
  if start==60 then return {plots={60,61,62,48,46}} end
  if start==61 then return {plots={61,62,48,46}} end
  return nil
 elseif index==50 then
  if start==43 then return {plots={43,42,44,70,71,72,73,74,47,46,50}} end
  if start==42 then return {plots={42,44,70,71,72,73,74,47,46,50}} end
  if start==44 then return {plots={44,70,71,72,73,74,47,46,50}} end
 end
 return nil
end
''')
        if phased:
            self.lua.execute('Automation={GetTime=function() return 0 end}')

    def run_ticks(self, count=20):
        for _ in range(count):
            self.c.RunNow()
        self.assertNotIn('脚本错误', self.c.GetStatus())

    def edges(self):
        return [(e.unit, e['from'], e.to) for e in self.w.moveEdges.values()]

    def test_failed_goal_is_not_retried_after_two_actual_moves(self):
        self.fixture()
        self.run_ticks()
        self.assertEqual(self.edges(), [(3,42,43),(3,43,42),(3,42,44)])
        self.assertEqual(sum(q.target==46 and q['from']==42 for q in self.w.pathQueries.values()), 1)

    def test_phased_planner_preserves_failed_goal_across_moves(self):
        self.fixture(phased=True)
        self.run_ticks()
        self.assertEqual(self.edges(), [(3,42,43),(3,43,42),(3,42,44)])
        self.assertEqual(sum(q.target==46 and q['from']==42 for q in self.w.pathQueries.values()), 1)

    def test_successful_goal_remains_available_for_next_step(self):
        self.fixture()
        self.w.failAt43=False
        self.run_ticks()
        self.assertEqual(self.edges()[:2], [(3,42,43),(3,43,60)])
        self.assertEqual([(q['from'],q.target) for q in self.w.pathQueries.values()][:2], [(42,46),(43,46)])

    def test_new_turn_retries_previous_failed_goal(self):
        self.fixture()
        self.run_ticks()
        self.w.turn+=1
        self.w.builderPlot=42
        self.w.builderMoves=2
        self.w.stopAfter=self.w.moveCount+1
        self.run_ticks()
        self.assertEqual(self.edges()[-1], (3,42,43))

    def test_busy_query_does_not_reject_goal_for_rest_of_turn(self):
        self.fixture()
        self.w.busyOnQuery=True
        self.c.RunNow()
        self.assertEqual(self.edges(), [])
        self.w.busy=False
        self.w.builderMoves=1.5
        self.w.stopAfter=1
        self.run_ticks()
        self.assertEqual(self.edges(), [(3,42,43)])

    def test_replacement_full_id_does_not_inherit_failed_goals(self):
        self.fixture()
        self.c.RunNow()
        self.c.RunNow()
        self.assertEqual(self.edges(), [(3,42,43)])
        self.lua.execute('TestWorld.objects.builder.GetID=function() return 65539 end')
        self.w.builderPlot=42
        self.w.builderMoves=2
        self.w.stopAfter=2
        self.run_ticks()
        self.assertEqual(self.edges()[-1], (65539,42,43))


class BuilderRejectedGoalPhaseFailureTests(unittest.TestCase):
    setUp = phases.BuilderRoutePhaseTests.setUp

    def test_validation_failure_does_not_index_cleared_target(self):
        self.c.RunNow()
        self.assertEqual(self.private.Searches()[3].phase, 'validate')
        self.w.enemyPlot=43
        self.c.RunNow()
        self.assertNotIn('脚本错误', self.c.GetStatus())
        self.assertTrue(all(r.op!=10 for r in self.w.unitRequests.values()))
        self.assertIsNone(self.private.Searches()[3])
