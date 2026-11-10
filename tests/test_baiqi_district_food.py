"""Exercise the real district chooser and final write boundary with native-shaped work rows."""
import unittest
from tests import test_baiqi_district_improvements as districts


class DistrictFoodTests(unittest.TestCase):
    def setUp(self):
        self.case = districts.DistrictImprovementTests(methodName='runTest')
        self.case.setUp()
        self.lua = self.case.lua
        self.w = self.case.w
        self.lua.execute('''
local w=TestWorld;local c=w.objects.city
w.placementFood=1;w.surplus=0;w.worker=1;w.workReads=0
YieldTypes.FOOD=1
w.plot.GetYield=function(_,kind)assert(kind==YieldTypes.FOOD);return w.placementFood end
c.GetGrowth=function()return {GetFoodSurplus=function()return w.surplus end}end
CityCommandTypes={MANAGE=40,PARAM_MANAGE_CITIZEN=41}
CityCommandResults={PLOTS=50,CITIZENS=51}
UI.GetInterfaceModeParameter=function(key)assert(key==41);return 9 end
CityManager.GetCommandTargets=function(city,kind,params)
 assert(city==c and kind==40 and params[41]==9)
 w.workReads=w.workReads+1;if w.onWorkRead then w.onWorkRead()end
 if w.badWork then return w.badWork()end
 return {[50]={[0]=42,[19]=76},[51]={[0]=w.worker,[19]=2}}
end
''')

    def test_real_placement_rejects_loss_of_one_worked_food_at_zero_surplus(self):
        self.case.run_city(0)
        self.assertEqual(self.w.workReads, 1)
        self.assertEqual(self.w.eligibilityChecks, 0)

    def test_worked_food_with_enough_margin_or_explicit_unworked_positive_is_allowed(self):
        for surplus, worker in [(1, 1), (5, 1), (-1, 0), (0, 0)]:
            with self.subTest(surplus=surplus, worker=worker):
                self.setUp()
                self.w.surplus, self.w.worker = surplus, worker
                self.case.run_city(1)
                self.assertEqual(self.w.workReads, 2)

    def test_zero_food_does_not_need_work_or_growth_ports(self):
        self.w.placementFood = 0
        self.lua.execute('CityManager.GetCommandTargets=nil;TestWorld.objects.city.GetGrowth=nil')
        self.case.run_city(1)
        self.assertEqual(self.w.workReads, 0)

    def test_unknown_positive_work_data_is_never_treated_as_explicit_zero(self):
        for change in [
            'TestWorld.worker=nil', 'TestWorld.worker=-1', 'TestWorld.worker=2',
            'TestWorld.worker=0.5', 'TestWorld.worker=0/0', 'TestWorld.worker="0"',
            'TestWorld.surplus=nil', 'TestWorld.surplus=math.huge',
            'TestWorld.badWork=function()error("read error")end',
            'TestWorld.badWork=function()return {[50]={[0]=99},[51]={[0]=0}}end',
            'TestWorld.badWork=function()return {[50]={[0]=42,[4]=42},[51]={[0]=0,[4]=0}}end',
            'CityCommandResults.CITIZENS=CityCommandResults.PLOTS',
        ]:
            with self.subTest(change=change):
                self.setUp()
                self.lua.execute(change)
                self.case.run_city(0)

    def test_final_native_recheck_uses_fresh_margin_worker_and_plot_food(self):
        for worker, margin, mutation in [
            (1, 1, 'w.surplus=0'), (0, 0, 'w.worker=1'),
            (1, 1, 'w.placementFood=2'), (0, 0, 'w.worker=nil'),
        ]:
            with self.subTest(mutation=mutation):
                self.setUp()
                self.w.worker, self.w.surplus = worker, margin
                self.lua.execute('TestWorld.shock=function()local w=TestWorld;' + mutation + ' end')
                self.case.run_city(0)
                self.assertEqual(self.w.eligibilityChecks, 2)
                self.assertEqual(self.w.workReads, 2)

    def test_fresh_work_read_cannot_cover_a_queue_change(self):
        self.w.worker = 0
        self.lua.execute('TestWorld.onWorkRead=function()if TestWorld.workReads==2 then TestWorld.queueSize=2 end end')
        self.case.run_city(0)
        self.assertEqual(self.w.workReads, 2)

    def test_multiple_legal_candidates_share_planning_read_only(self):
        self.w.worker = 0
        self.lua.execute('''
local first=GameInfo.Districts[777];local second={Hash=778,Index=3,DistrictType='DISTRICT_DAM'}
GameInfo.Districts[778]=second
getmetatable(GameInfo.Districts).__call=function()
 local n=0;return function()n=n+1;if n==1 then return first elseif n==2 then return second end end
end
TestWorld.objects.city:GetBuildQueue().CanProduce=function(_,hash)return hash==777 or hash==778 end
TestWorld.objects.city:GetBuildQueue().HasBeenPlaced=function()return false end
CityManager.CanStartOperation=function(_,_,params)
 local hash=params[CityOperationTypes.PARAM_DISTRICT_TYPE];assert(hash==777 or hash==778)
 TestWorld.eligibilityChecks=TestWorld.eligibilityChecks+1;return true
end
''')
        self.case.run_city(1)
        self.assertEqual(self.w.workReads, 2)
        self.assertEqual(self.w.eligibilityChecks, 3)

    def test_repair_and_busy_queue_do_not_read_placement_food(self):
        self.w.repair = True
        self.case.run_city(1)
        self.assertEqual(self.w.workReads, 0)
        self.setUp()
        self.w.queueSize = 2
        self.case.run_city(0)
        self.assertEqual(self.w.workReads, 0)


if __name__ == '__main__':
    unittest.main()
