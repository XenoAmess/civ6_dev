"""Controller-only proposal protocol and reload tests; Core tested separately."""
from pathlib import Path
import unittest
from lupa.lua51 import LuaRuntime

ROOT=Path(__file__).resolve().parents[1]


class SettlerGoalsUITests(unittest.TestCase):
    def setUp(self):
        self.lua=LuaRuntime(unpack_returned_tuples=True)
        for name in ('tests/lua/mock_world.lua','tests/lua/mock_movement.lua',
                     'tests/lua/mock_path_ranking.lua','mod/Baiqi/Lua/BaiqiConfig.lua',
                     'mod/Baiqi/Lua/BaiqiPolicy.lua','mod/Baiqi/Lua/BaiqiPlanner.lua',
                     'mod/Baiqi/Lua/BaiqiController.lua'):
            self.lua.execute((ROOT/name).read_text(encoding='utf-8'))
        self.w=self.lua.globals().TestWorld
        self.w.withBuilder,self.w.withSettler=False,True
        self.c=self.lua.globals().BaiqiController

    def requests(self):
        return [(a.unit,a.op)for a in self.w.unitRequests.values()]

    def paths(self):
        return [(a.unit,a.target)for a in self.w.pathQueries.values()]

    def no_move_or_found(self):
        self.assertFalse(any(op in (10,11)for _,op in self.requests()))
        self.assertTrue(all(unit!=1 for unit,_ in self.requests()))

    def test_recreated_controller_recovers_goal_after_hint_disappears(self):
        self.c.RunNow()
        self.assertEqual(self.paths(),[(2,46)])
        self.assertEqual(self.w.goalProposals['2'].plot,46)
        # Fixture applies the first requested step, then reconstructs the entire
        # controller while keeping the independent proposal service's data.
        self.w.settlerPlot,self.w.turn=43,2
        self.lua.execute('TestWorld.paths[46]={43,60,61,62,48,46};TestWorld.settlementRecommendations={47}')
        self.lua.execute((ROOT/'mod/Baiqi/Lua/BaiqiController.lua').read_text(encoding='utf-8'))
        self.c=self.lua.globals().BaiqiController
        self.c.RunNow()
        self.assertEqual(self.paths(),[(2,46),(2,46)])
        self.assertEqual(self.requests(),[(2,10),(2,10)])
        self.assertEqual((self.w.unitRequests[2].params[14],self.w.unitRequests[2].params[15]),(4,3))

    def test_read_error_or_malformed_proposal_blocks_movement(self):
        responses=(
            "error('READ_FAILED')",
            "return 'READY',{unitID=4,unitType='UNIT_SETTLER',plot=46,x=8,y=3}",
            "return 'READY',{unitID=2,unitType='UNIT_SETTLER',plot=46,x=8,y=3,extra=true}",
            "return 'READY',{unitID=2,unitType='UNIT_SETTLER',plot=46,x=0/0,y=3}",
            "return 'READY',setmetatable({unitID=2,unitType='UNIT_SETTLER',plot=46,x=8,y=3},{})",
        )
        for response in responses:
            with self.subTest(response=response):
                self.setUp();self.lua.execute('ExposedMembers.BaiqiSettlerGoalsBridge.Read=function()'+response+' end')
                self.c.RunNow();self.no_move_or_found();self.assertEqual(self.paths(),[])

    def test_remember_wrong_target_or_error_never_dispatches_move(self):
        for response in ("return 'UNAVAILABLE'","error('WRITE_UNKNOWN')",
                         "return 'READY',{unitID=2,unitType='UNIT_SETTLER',plot=47,x=8,y=4}",
                         "return 'READY',nil"):
            with self.subTest(response=response):
                self.setUp();self.lua.execute('ExposedMembers.BaiqiSettlerGoalsBridge.Remember=function()'+response+' end')
                self.c.RunNow();self.no_move_or_found();self.assertEqual(self.paths(),[(2,46)])

    def test_feature_added_at_restored_destination_is_not_destroyed_by_founding(self):
        self.lua.execute("TestWorld.goalProposals['2']={unitID=2,unitType='UNIT_SETTLER',plot=46,x=8,y=3};Map.GetPlotByIndex(46).GetFeatureType=function()return 2 end")
        self.w.settlerPlot=46
        self.c.RunNow()
        self.assertFalse(any(op==11 for _,op in self.requests()))
        self.assertIsNone(self.w.goalProposals['2'])
        self.assertTrue(all(unit!=1 for unit,_ in self.requests()))

    def test_foreign_owned_restored_site_replans_without_order_to_old_site(self):
        self.lua.execute("TestWorld.goalProposals['2']={unitID=2,unitType='UNIT_SETTLER',plot=46,x=8,y=3};TestWorld.siteOwners[46]=8")
        self.c.RunNow()
        self.assertEqual(self.paths(),[(2,47)])
        self.assertEqual(self.w.goalProposals['2'].plot,47)
        self.assertEqual(self.requests(),[(2,10)])

    def test_missing_unknown_or_metatable_bridge_cannot_bypass_storage(self):
        for change in ('ExposedMembers.BaiqiSettlerGoalsBridge=nil',
                       'ExposedMembers.BaiqiSettlerGoalsBridge.version=2',
                       'setmetatable(ExposedMembers.BaiqiSettlerGoalsBridge,{})'):
            with self.subTest(change=change):
                self.setUp();self.lua.execute(change);self.c.RunNow();self.no_move_or_found()
                self.assertEqual(self.paths(),[])


if __name__=='__main__':unittest.main()
