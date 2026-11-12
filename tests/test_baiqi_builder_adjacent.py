"""Exercise the separate Gathering Storm operation through real controller writers."""
from pathlib import Path
import os
import unittest

from lupa.lua51 import LuaRuntime

ROOT = Path(__file__).resolve().parents[1]


class BuilderAdjacentTests(unittest.TestCase):
    def setUp(self):
        self.lua = LuaRuntime(unpack_returned_tuples=True)
        for name in ('tests/lua/mock_world.lua', 'tests/lua/mock_movement.lua',
                     'tests/lua/mock_path_ranking.lua', 'mod/Baiqi/Lua/BaiqiConfig.lua',
                     'mod/Baiqi/Lua/BaiqiPolicy.lua', 'mod/Baiqi/Lua/BaiqiPlanner.lua'):
            path = Path(os.environ.get('BAIQI_ADJACENT_POLICY', str(ROOT / name))) if name.endswith('BaiqiPolicy.lua') else ROOT / name
            self.lua.execute(path.read_text(encoding='utf-8'))
        self.lua.execute('''
local w=TestWorld
UnitOperationTypes.BUILD_IMPROVEMENT_ADJACENT=18
UnitOperationResults={PLOTS=99}
w.adjacentTargets={[0]=43};w.targetReads=0;w.adjacentQueries=0
w.adjacentCan=true;w.districts={};w.improvements={};w.recPlot=43;w.recHash=505
local ski={Index=50,Hash=505,ImprovementType='IMPROVEMENT_SKI_RESORT'}
GameInfo.Improvements.IMPROVEMENT_SKI_RESORT=ski
GameInfo.Improvements[50]=ski;GameInfo.Improvements[505]=ski
for _,id in ipairs({42,43,44,45,46,47,48,50,60,61,62,70,71,72,73,74})do
 local p=Map.GetPlotByIndex(id)
 p.GetDistrictType=function()return w.districts[id]or -1 end
 p.GetImprovementType=function()return w.improvements[id]or -1 end
end
Map.GetAdjacentPlot=function(x,y,d)
 local offsets={{1,0},{0,1},{-1,1},{-1,0},{0,-1},{1,-1}}
 local delta=assert(offsets[d+1]);return Map.GetPlot(x+delta[1],y+delta[2])
end
w.objects.city.GetCityAI=function()return {GetImprovementRecommendationsForBuilder=function()
 local rows={};for i=1,(w.recCount or 1)do rows[i]={ImprovementLocation=w.recPlot,ImprovementHash=w.recHash}end;return rows
end}end
UnitManager.GetOperationTargets=function(unit,op,params)
 assert(unit==w.objects.builder and op==18 and params[16]==505 and params[14]==nil and params[15]==nil)
 w.targetReads=w.targetReads+1
 if w.targetsError then error('native targets unavailable')end
 if w.targetsMissing then return {}end
 return {[99]=w.adjacentTargets}
end
local original=UnitManager.CanStartOperation
UnitManager.CanStartOperation=function(unit,op,mode,params,...)
 if op~=18 then return original(unit,op,mode,params,...)end
 assert(unit==w.objects.builder and mode==nil and params[14]==3 and params[15]==3 and params[16]==505)
 w.adjacentQueries=w.adjacentQueries+1
 if w.onAdjacentQuery then w.onAdjacentQuery()end
 if w.adjacentError then error('native qualification unavailable')end
 return w.adjacentCan
end
''')
        self.private = self.lua.execute(
            Path(os.environ.get('BAIQI_ADJACENT_CONTROLLER', str(ROOT / 'mod/Baiqi/Lua/BaiqiController.lua'))).read_text(encoding='utf-8')
            + '\nreturn {Adjacent=BuilderAdjacentCandidates,Request=RequestCivilian,Targets=BuilderTargets,'
            + 'Builder=ProcessBuilder,Pending=function()return pendingUnits end}\n')
        self.w = self.lua.globals().TestWorld
        self.g = self.lua.globals()
        self.g.BaiqiController.RunNow(False)
        self.ctx = self.lua.table_from(dict(player=7, localPlayer=7, isBaiqi=True,
                                            activeTurn=True, enabled=True))

    def write(self, operation='BUILD_IMPROVEMENT_ADJACENT', plot=43, unit=None):
        return self.private.Request(self.ctx, self.lua.table(), unit or self.w.objects.builder,
                                    operation, self.g.Map.GetPlotByIndex(plot), 505)

    def build(self):
        return self.private.Builder(self.ctx, self.w.objects.player, self.lua.table(), self.w.objects.builder)

    def requests(self, op=None):
        return [r for r in self.w.unitRequests.values() if op is None or r.op == op]

    def test_actual_sparse_target_producer_and_one_pending_writer(self):
        self.g.PrivatePending = self.private.Pending()
        self.lua.execute('''
local original=UnitManager.RequestOperation
UnitManager.RequestOperation=function(unit,op,params)
 if op==18 then assert(PrivatePending[3].kind=='BUILD_IMPROVEMENT_ADJACENT'and PrivatePending[3].plot==43)end
 return original(unit,op,params)
end
''')
        self.build()
        self.assertEqual((self.w.targetReads, self.w.adjacentQueries), (1, 2))
        r = self.requests(18)[0]
        self.assertEqual((r.unit, r.op, r.params[14], r.params[15], r.params[16]), (3, 18, 3, 3, 505))
        self.build()
        self.assertEqual(len(self.requests()), 1)
        self.assertIsNotNone(self.private.Pending()[3])

    def test_adjacent_precedes_ordinary_local_improvement(self):
        self.lua.execute('''
TestWorld.localBuildQueries=0
local original=UnitManager.CanStartOperation
UnitManager.CanStartOperation=function(unit,op,...)
 if op==12 then TestWorld.localBuildQueries=TestWorld.localBuildQueries+1;return false end
 return original(unit,op,...)
end
''')
        self.build()
        self.assertEqual(self.w.localBuildQueries, 0)
        self.assertEqual([r.op for r in self.requests()], [18])

    def test_ordinary_build_keeps_current_plot_requirement(self):
        self.assertFalse(self.write('BUILD_IMPROVEMENT')[0])
        self.assertEqual(self.requests(), [])
        self.assertEqual(self.w.adjacentQueries, 0)

    def test_military_and_other_civilians_never_gain_adjacent_operation(self):
        for kind in ('UNIT_WARRIOR', 'UNIT_SETTLER', 'UNIT_TRADER', 'UNIT_MISSIONARY',
                     'UNIT_APOSTLE', 'UNIT_INQUISITOR', 'UNIT_GURU', 'UNIT_GREAT_ENGINEER'):
            with self.subTest(kind=kind):
                self.assertFalse(self.g.BaiqiPolicy.ActionAllowed(kind, 'BUILD_IMPROVEMENT_ADJACENT'))
        self.assertFalse(self.write(unit=self.w.objects.army)[0])
        self.assertEqual(self.requests(), [])

    def test_escort_or_foreign_actor_rejected_before_qualification(self):
        for change in ('TestWorld.formation=2', 'TestWorld.objects.builder.GetOwner=function()return 8 end'):
            with self.subTest(change=change):
                self.setUp(); self.lua.execute(change)
                self.assertFalse(self.write()[0])
                self.assertEqual((len(self.requests()), self.w.adjacentQueries), (0, 0))

    def test_target_foreign_hidden_fogged_or_occupied_is_not_authorized(self):
        for change in ('TestWorld.siteOwners[43]=8', 'TestWorld.hidden[43]=true',
                       'TestWorld.fogged[43]=true', 'TestWorld.improvements[43]=1',
                       'TestWorld.districts[43]=0'):
            with self.subTest(change=change):
                self.setUp(); self.lua.execute(change)
                self.assertFalse(self.write()[0])
                self.assertEqual((len(self.requests()), self.w.adjacentQueries), (0, 0))

    def test_distance_and_exact_improvement_kind_are_required(self):
        self.assertFalse(self.write(plot=45)[0])
        self.lua.execute("GameInfo.Improvements.IMPROVEMENT_SKI_RESORT.ImprovementType='IMPROVEMENT_FARM'")
        self.assertFalse(self.write()[0])
        self.assertEqual(self.requests(), [])

    def test_missing_gs_bindings_preserve_no_adjacent_submission(self):
        for change in ('UnitOperationTypes.BUILD_IMPROVEMENT_ADJACENT=nil',
                       'UnitManager.GetOperationTargets=nil', 'UnitOperationResults.PLOTS=nil'):
            with self.subTest(change=change):
                self.setUp(); self.lua.execute(change)
                self.assertIsNone(self.private.Adjacent(self.w.objects.builder))
                self.assertEqual(self.requests(), [])

    def test_target_exception_missing_result_and_bad_id_are_not_known_empty(self):
        for change in ('TestWorld.targetsError=true', 'TestWorld.targetsMissing=true',
                       'TestWorld.adjacentTargets={[0]=true}'):
            with self.subTest(change=change):
                self.setUp(); self.lua.execute(change)
                self.assertIsNone(self.private.Adjacent(self.w.objects.builder))
                self.assertEqual(self.requests(), [])
        self.setUp(); self.lua.execute('TestWorld.adjacentTargets={}')
        self.assertEqual(len(self.private.Adjacent(self.w.objects.builder)), 0)

    def test_false_nonboolean_and_exception_from_final_qualification_no_write(self):
        for change in ('TestWorld.adjacentCan=false', "TestWorld.adjacentCan='true'",
                       'TestWorld.adjacentError=true'):
            with self.subTest(change=change):
                self.setUp(); self.lua.execute(change)
                self.assertFalse(self.write()[0])
                self.assertEqual(self.requests(), [])

    def test_final_boundary_rechecks_actor_target_metadata_and_native_ports(self):
        changes = ('TestWorld.siteOwners[43]=8', 'TestWorld.formation=2', 'TestWorld.busy=true',
                   'TestWorld.districts[43]=0', 'TestWorld.improvements[43]=1',
                   'TestWorld.fogged[43]=true',
                   'GameInfo.Improvements.IMPROVEMENT_SKI_RESORT.Index=51',
                   'GameInfo.Improvements.IMPROVEMENT_SKI_RESORT.Hash=506',
                   'UnitOperationTypes.BUILD_IMPROVEMENT_ADJACENT=19',
                   "UnitManager.RequestOperation=function()error('must not enter replaced writer')end")
        for change in changes:
            with self.subTest(change=change):
                self.setUp()
                self.lua.execute('TestWorld.onAdjacentQuery=function() ' + change + ' end')
                self.assertFalse(self.write()[0])
                self.assertEqual(self.requests(), [])

    def test_rejected_writer_does_not_fall_through_to_movement(self):
        self.lua.execute('''
TestWorld.onAdjacentQuery=function()
 if TestWorld.adjacentQueries==2 then TestWorld.siteOwners[43]=8 end
end
''')
        self.build()
        self.assertEqual(self.w.adjacentQueries, 2)
        self.assertEqual(self.requests(), [])

    def test_remote_ai_mountain_uses_walkable_staging_without_removing_improvement(self):
        self.lua.execute('TestWorld.adjacentTargets={};TestWorld.recPlot=60;TestWorld.improvements[43]=1')
        targets = self.private.Targets(self.ctx, self.w.objects.player, self.w.objects.builder)
        self.assertEqual(targets[1].index, 43)
        self.assertNotIn(60, [r.index for r in targets.values()])
        self.build()
        self.assertEqual([r.op for r in self.requests()], [10])
        self.assertEqual((self.requests()[0].params[14], self.requests()[0].params[15]), (3, 3))
        self.assertEqual(self.w.improvements[43], 1)

    def test_ordinary_hint_keeps_original_destination(self):
        self.lua.execute('TestWorld.recPlot=60;TestWorld.recHash=nil')
        targets = self.private.Targets(self.ctx, self.w.objects.player, self.w.objects.builder)
        self.assertEqual([r.index for r in targets.values()], [60])

    def test_raw_target_and_recommendation_bounds_stop_before_writes(self):
        self.lua.execute('TestWorld.adjacentTargets={};for i=1,129 do TestWorld.adjacentTargets[i]=43 end')
        self.assertIsNone(self.private.Adjacent(self.w.objects.builder))
        self.assertEqual(self.requests(), [])
        self.lua.execute('TestWorld.recPlot=60;TestWorld.recCount=129')
        self.assertEqual(len(self.private.Targets(self.ctx, self.w.objects.player, self.w.objects.builder)), 0)


if __name__ == '__main__':
    unittest.main()
