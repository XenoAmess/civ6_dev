import unittest
import test_baiqi_path_ranking as ranking


class BuilderEscortInvalidationTests(unittest.TestCase):
    setUp = ranking.PathRankingTests.setUp

    def test_escort_during_path_query_does_not_reject_goal_after_detaching(self):
        self.lua.execute('''
local w=TestWorld
w.builderRecommendations={43};w.firstQuery=true
local originalGetPath=UnitManager.GetMoveToPathEx
UnitManager.GetMoveToPathEx=function(unit,index)
 if w.firstQuery then
  w.firstQuery=false;w.formation=2
  w.pathQueries[#w.pathQueries+1]={unit=unit:GetID(),target=index}
  return nil
 end
 return originalGetPath(unit,index)
end
''')
        self.c.RunNow()
        self.assertEqual(len(self.w.unitRequests),0)
        self.lua.execute('TestWorld.formation=1;TestWorld.builderMoves=1')
        self.c.RunNow()
        self.assertEqual([(q.unit,q.target) for q in self.w.pathQueries.values()],[(3,43),(3,43)])
        self.assertEqual(len(self.w.unitRequests),1)
        request=self.w.unitRequests[1]
        self.assertEqual((request.unit,request.op,request.params[14],request.params[15]),(3,10,3,3))
