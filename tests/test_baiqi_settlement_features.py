"""Settlement recommendations and retained goals use current feature metadata."""
from pathlib import Path
import unittest
from lupa.lua51 import LuaRuntime

ROOT = Path(__file__).resolve().parents[1]


class SettlementFeatureTests(unittest.TestCase):
    def setUp(self):
        self.lua = LuaRuntime(unpack_returned_tuples=True)
        for name in ('tests/lua/mock_world.lua', 'tests/lua/mock_movement.lua',
                     'tests/lua/mock_path_ranking.lua', 'mod/Baiqi/Lua/BaiqiConfig.lua',
                     'mod/Baiqi/Lua/BaiqiPolicy.lua', 'mod/Baiqi/Lua/BaiqiPlanner.lua'):
            self.lua.execute((ROOT / name).read_text(encoding='utf-8'))
        source = (ROOT / 'mod/Baiqi/Lua/BaiqiController.lua').read_text(encoding='utf-8')
        self.sites, self.allowed = self.lua.execute(
            source + '\nreturn SettlementSites,SettlementFeatureAllowed')
        self.w = self.lua.globals().TestWorld
        self.controller = self.lua.globals().BaiqiController
        self.controller.RunNow(False)
        self.lua.execute("""
            GameInfo.Features={}
            local plot=Map.GetPlotByIndex(46)
            plot.GetFeatureType=function()return 2 end
            GameInfo.Features[2]={Index=2,FeatureType='FEATURE_JUNGLE',
              Settlement=true,NaturalWonder=false,Impassable=false}
        """)

    def indexes(self, preferred=None):
        return [r.index for r in self.sites(
            self.w.objects.player, self.lua.table(), False, self.lua.table(), 2, preferred).values()]

    def test_native_recommended_ordinary_features_are_considered(self):
        for name in ('FEATURE_JUNGLE', 'FEATURE_FOREST', 'FEATURE_MARSH',
                     'FEATURE_FLOODPLAINS', 'FEATURE_FLOODPLAINS_PLAINS'):
            with self.subTest(name=name):
                self.lua.globals().GameInfo.Features[2].FeatureType = name
                self.assertIn(46, self.indexes())

    def test_oasis_wonder_and_impassable_features_stay_rejected(self):
        for change in ("Settlement=false", "NaturalWonder=true", "Impassable=true"):
            with self.subTest(change=change):
                self.setUp()
                self.lua.execute('GameInfo.Features[2].' + change)
                self.assertNotIn(46, self.indexes(46))

    def test_unknown_metadata_does_not_imply_permission(self):
        for change in ("Settlement=nil", "NaturalWonder=nil", "Impassable=nil",
                       "FeatureType=nil", "FeatureType=''", "Index=3", "Settlement=1"):
            with self.subTest(change=change):
                self.setUp()
                self.lua.execute('GameInfo.Features[2].' + change)
                self.assertNotIn(46, self.indexes(46))
        self.lua.execute('GameInfo.Features[2]=nil')
        self.assertNotIn(46, self.indexes())

    def test_feature_lookup_exceptions_are_contained(self):
        for script in (
                "Map.GetPlotByIndex(46).GetFeatureType=function()error('unavailable')end",
                "GameInfo.Features=setmetatable({}, {__index=function()error('unavailable')end})"):
            with self.subTest(script=script):
                self.setUp()
                self.lua.execute(script)
                self.assertNotIn(46, self.indexes(46))

    def test_invalid_feature_indexes_are_rejected_and_bare_land_keeps_working(self):
        for expression in ('0/0', 'math.huge', '-math.huge', '2.5', '-2', 'nil', "'2'"):
            with self.subTest(expression=expression):
                self.lua.execute('Map.GetPlotByIndex(46).GetFeatureType=function()return ' + expression + ' end')
                self.assertNotIn(46, self.indexes())
        self.lua.execute('Map.GetPlotByIndex(46).GetFeatureType=function()return -1 end')
        self.assertIn(46, self.indexes())

    def test_feature_permission_does_not_bypass_visibility_owner_or_threat(self):
        for change in ('TestWorld.hidden[46]=true', 'TestWorld.siteOwners[46]=8',
                       'TestWorld.enemyPlot=46'):
            with self.subTest(change=change):
                self.setUp()
                self.lua.execute(change)
                self.assertNotIn(46, self.indexes(46))

    def test_retained_feature_goal_survives_changed_recommendations(self):
        self.w.withBuilder, self.w.withSettler = False, True
        self.controller.RunNow()
        self.assertEqual(self.w.pathQueries[1].target, 46)
        self.assertEqual(self.w.goalProposals['2'].plot, 46)
        self.w.turn += 1
        self.w.settlementRecommendations = self.lua.table_from([47])
        self.w.settlerPlot = 47
        # Isolate revalidation from pending native movement completion.
        self.w.unitRequests = self.lua.table()
        self.controller.RunNow()
        self.controller.RunNow()
        self.assertIsNotNone(self.w.goalProposals['2'])
        self.assertEqual(self.w.goalProposals['2'].plot, 46)
        self.assertIn(46, self.indexes(46))
        self.assertNotIn('脚本错误', self.controller.GetStatus())

    def test_retained_goal_rechecks_changed_feature_metadata(self):
        self.w.withBuilder, self.w.withSettler = False, True
        self.controller.RunNow()
        self.assertEqual(self.w.goalProposals['2'].plot, 46)
        self.w.turn += 1
        self.w.settlerPlot = 47
        self.lua.execute('GameInfo.Features[2].Settlement=false;TestWorld.settlementRecommendations={}')
        self.controller.RunNow()
        self.controller.RunNow()
        self.assertIsNone(self.w.goalProposals['2'])
        self.assertFalse(any(r.op == 11 for r in self.w.unitRequests.values()))

    def test_native_found_denial_still_blocks_feature_goal(self):
        self.w.withBuilder, self.w.withSettler = False, True
        self.controller.RunNow()
        self.w.turn += 1
        self.w.settlerPlot = 46
        self.lua.execute('''
            local old=UnitManager.CanStartOperation
            UnitManager.CanStartOperation=function(u,op,...)
              if op==11 then return false end
              return old(u,op,...)
            end
        ''')
        self.controller.RunNow()
        self.assertFalse(any(r.op == 11 for r in self.w.unitRequests.values()))
        self.assertNotIn('脚本错误', self.controller.GetStatus())


if __name__ == '__main__':
    unittest.main()
