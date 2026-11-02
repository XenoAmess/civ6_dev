"""Actual Controller submissions after native qualification changes the target."""
import test_baiqi_path_safety_cache as path_safety
import unittest


class LateMoveTests(unittest.TestCase):
    setUp = path_safety.PathSafetyCacheTests.setUp

    def mutate_on_move_qualification(self, change):
        self.w.withBuilder, self.w.withSettler = False, True
        self.lua.execute('''
            TestWorld.settlementRecommendations={46}
            TestWorld.lateMutationCalls=0
            local original=UnitManager.CanStartOperation
            UnitManager.CanStartOperation=function(unit,op,mode,params)
                local result=original(unit,op,mode,params)
                if op==UnitOperationTypes.MOVE_TO then
                    TestWorld.lateMutationCalls=TestWorld.lateMutationCalls+1
                    MUTATION
                end
                return result
            end
        '''.replace('MUTATION', change))
        self.c.RunNow()
        self.assertEqual(self.w.lateMutationCalls, 1)
        self.assertEqual(len(self.w.pathQueries), 1)
        for request in self.w.unitRequests.values():
            self.assertNotEqual(request.unit, 1)
            self.assertNotEqual(request.op, 10)

    def test_enemy_after_qualification_blocks_move(self):
        self.mutate_on_move_qualification('TestWorld.enemyPlot=43')

    def test_hidden_target_after_qualification_blocks_move(self):
        self.mutate_on_move_qualification('TestWorld.hidden[43]=true')

    def test_foreign_border_after_qualification_blocks_move(self):
        self.mutate_on_move_qualification('TestWorld.siteOwners[43]=8')

    def test_new_civilian_occupant_after_qualification_blocks_move(self):
        self.mutate_on_move_qualification('''
            local originalUnits=Units.GetUnitsInPlot
            Units.GetUnitsInPlot=function(plot)
                if plot:GetIndex()==43 then return {TestWorld.objects.builder} end
                return originalUnits(plot)
            end
        ''')

    def test_changed_unit_position_after_qualification_blocks_move(self):
        self.mutate_on_move_qualification('TestWorld.settlerPlot=44')

    def test_core_busy_after_qualification_blocks_move(self):
        self.mutate_on_move_qualification('TestWorld.busy=true')

    def test_inactive_context_after_qualification_blocks_move(self):
        self.mutate_on_move_qualification('TestWorld.strategic=false')


if __name__ == '__main__':
    unittest.main()
