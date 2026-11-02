"""Verify actual command effects and fresh post-qualification safety facts."""
import unittest
import test_baiqi_path_safety_cache as path_safety
import test_baiqi_trade_ranking as trade_ranking


class MoveCommandBoundaryTests(unittest.TestCase):
    setUp_world = path_safety.PathSafetyCacheTests.setUp

    def setUp(self):
        self.setUp_world()
        self.w.withBuilder, self.w.withSettler = False, True

    def move(self):
        return self.private.RequestCivilian(None, self.lua.table(), self.w.objects.settler,
                                             'MOVE_TO', self.lua.globals().Map.GetPlotByIndex(43))

    def test_final_move_safety_reads_neighborhood_once_not_before_and_after_query(self):
        self.lua.execute('''
            TestWorld.commandReads={}
            local original=Units.GetUnitsInPlot
            Units.GetUnitsInPlot=function(plot)
                local id=plot:GetIndex()
                TestWorld.commandReads[id]=(TestWorld.commandReads[id] or 0)+1
                return original(plot)
            end
        ''')
        success, _ = self.move()
        self.assertTrue(success)
        self.assertEqual((self.w.unitRequests[1].unit, self.w.unitRequests[1].op), (2, 10))
        neighbors = [n for index, n in self.w.commandReads.items() if index != 43]
        self.assertGreater(len(neighbors), 1)
        self.assertLessEqual(max(neighbors), 1)
        self.assertLessEqual(self.w.commandReads[43], 3)

    def test_hidden_move_target_never_reaches_native_qualification(self):
        self.w.hidden[43] = True
        self.lua.execute('''
            TestWorld.moveQualifications=0
            local original=UnitManager.CanStartOperation
            UnitManager.CanStartOperation=function(unit,op,...)
                if op==UnitOperationTypes.MOVE_TO then TestWorld.moveQualifications=TestWorld.moveQualifications+1 end
                return original(unit,op,...)
            end
        ''')
        success, _ = self.move()
        self.assertFalse(success)
        self.assertEqual((self.w.moveQualifications, len(self.w.unitRequests)), (0, 0))


class TradeCommandBoundaryTests(unittest.TestCase):
    setUp = trade_ranking.TradeRankingTests.setUp
    routes = trade_ranking.TradeRankingTests.routes
    destination = trade_ranking.TradeRankingTests.destination

    def mutate_at_final_qualification(self, change):
        self.lua.execute('''
            TestWorld.finalTradeMutation=0
            local chosen=0
            TestWorld.tradeOnQualify=function(q)
                if q.x==5 and q.y==3 then
                    chosen=chosen+1
                    if chosen==2 then
                        TestWorld.finalTradeMutation=TestWorld.finalTradeMutation+1
                        MUTATION
                    end
                end
                return true
            end
        '''.replace('MUTATION', change))
        self.c.RunNow()
        self.assertEqual(self.w.finalTradeMutation, 1)
        self.assertEqual(self.routes(), [])
        self.assertEqual([r.op for r in self.w.unitRequests.values()], [17])

    def test_enemy_appearing_during_final_qualification_blocks_route(self):
        self.mutate_at_final_qualification('TestWorld.tradeEnemy=45')

    def test_capacity_lost_during_final_qualification_blocks_route(self):
        self.mutate_at_final_qualification('TestWorld.tradeCapacity=0')

    def test_missing_destination_in_native_path_does_not_bypass_destination_safety(self):
        self.lua.execute('TestWorld.tradeRoutePaths[67]={42}')
        self.mutate_at_final_qualification('TestWorld.tradeEnemy=45')

    def test_route_changed_during_qualification_is_queried_again(self):
        self.lua.execute('''
            local extra={}
            for _,c in ipairs({{57,4,5},{58,5,4}}) do
                local id,x,y=c[1],c[2],c[3]
                extra[id]={GetIndex=function() return id end,GetX=function() return x end,
                    GetY=function() return y end,GetOwner=function() return 7 end}
            end
            local byIndex,byXY=Map.GetPlotByIndex,Map.GetPlot
            Map.GetPlotByIndex=function(id) return extra[id] or byIndex(id) end
            Map.GetPlot=function(x,y)
                for _,p in pairs(extra) do if p:GetX()==x and p:GetY()==y then return p end end
                return byXY(x,y)
            end
        ''')
        self.mutate_at_final_qualification('''
            TestWorld.tradeRoutePaths[67]={42,52,53,56,57,58,45}
            TestWorld.tradeEnemy=55
        ''')

    def test_selected_route_has_no_duplicate_outer_qualification(self):
        self.c.RunNow()
        self.assertEqual(self.destination(), (5, 3))
        self.assertEqual(len(self.w.tradeQualifications), 2)
        self.assertTrue(all(q.x == 5 and q.y == 3 for q in self.w.tradeQualifications.values()))


if __name__ == '__main__':
    unittest.main()
