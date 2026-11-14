"""Current proposal preference remains distinct from fresh write permission."""
from pathlib import Path
import unittest
from lupa.lua51 import LuaRuntime

ROOT=Path(__file__).resolve().parents[1]


class DirectSettlerGoalTests(unittest.TestCase):
    candidate_source=None

    def setUp(self):
        self.lua=LuaRuntime(unpack_returned_tuples=True)
        for name in ('tests/lua/mock_world.lua','tests/lua/mock_movement.lua',
                     'tests/lua/mock_path_ranking.lua','mod/Baiqi/Lua/BaiqiConfig.lua',
                     'mod/Baiqi/Lua/BaiqiPolicy.lua','mod/Baiqi/Lua/BaiqiPlanner.lua'):
            self.lua.execute((ROOT/name).read_text(encoding='utf-8'))
        source=self.candidate_source
        if source is None:source=(ROOT/'mod/Baiqi/Lua/BaiqiController.lua').read_text(encoding='utf-8')
        source+='''
local originalSupport=KnownExpansionSupport
KnownExpansionSupport=function(plot,...)
 local key=plot and plot:GetIndex()or-1
 TestWorld.supportReads[key]=(TestWorld.supportReads[key]or 0)+1
 return originalSupport(plot,...)
end
'''
        self.lua.execute('TestWorld.supportReads={}');self.lua.execute(source)
        self.lua.execute('''
local w=TestWorld;w.withBuilder=false;w.withSettler=true;w.hintReads=0
w.goalProposals['2']={unitID=2,unitType='UNIT_SETTLER',plot=46,x=8,y=3}
local old=w.objects.player.GetGrandStrategicAI
w.objects.player.GetGrandStrategicAI=function(self)
 local ai=old(self);return{GetSettlementRecommendations=function(_,n)
  w.hintReads=w.hintReads+1;return ai:GetSettlementRecommendations(n)
 end}
end
''')
        self.w=self.lua.globals().TestWorld;self.c=self.lua.globals().BaiqiController

    def step(self):
        self.c.RunNow();self.assertNotIn('脚本错误',self.c.GetStatus())
        self.assertTrue(all(row.unit!=1 for row in self.w.unitRequests.values()))

    def moves(self):return[(r.unit,r.params[14],r.params[15])for r in self.w.unitRequests.values()if r.op==10]

    def test_live_retained_goal_reads_support_once_and_no_hints(self):
        self.step()
        self.assertEqual(self.moves(),[(2,3,3)])
        self.assertEqual(self.w.supportReads[46],1)
        self.assertEqual(self.w.hintReads,0)

    def test_unreachable_preferred_continues_without_rechecking_tested_goal(self):
        self.w.paths[46]=False
        self.step();self.assertEqual(self.moves(),[]);self.assertEqual(self.w.hintReads,0)
        self.step();self.assertEqual(self.moves(),[(2,2,4)])
        self.assertEqual(self.w.supportReads[46],1)
        self.assertEqual(self.w.hintReads,1)

    def test_other_settler_reservation_blocks_direct_preferred(self):
        self.w.secondSettler=True
        self.lua.execute("TestWorld.goalProposals['4']={unitID=4,unitType='UNIT_SETTLER',plot=46,x=8,y=3}")
        self.step();self.step()
        paths=[(r.unit,r.target)for r in self.w.pathQueries.values()]
        self.assertEqual(paths,[(2,46),(4,47)])

    def test_unknown_remember_still_prevents_movement(self):
        self.lua.execute("ExposedMembers.BaiqiSettlerGoalsBridge.Remember=function()return'UNAVAILABLE'end")
        self.step();self.assertEqual(self.moves(),[])

    def test_escort_change_during_native_qualification_prevents_move(self):
        self.lua.execute('''
local old=UnitManager.CanStartOperation
UnitManager.CanStartOperation=function(unit,op,...)
 if op==UnitOperationTypes.MOVE_TO then TestWorld.formation=2 end
 return old(unit,op,...)
end
''')
        self.step();self.assertEqual(self.moves(),[])

    def test_target_step_owner_change_during_qualification_prevents_move(self):
        self.lua.execute('''
local old=UnitManager.CanStartOperation
UnitManager.CanStartOperation=function(unit,op,...)
 if op==UnitOperationTypes.MOVE_TO then TestWorld.siteOwners[43]=8 end
 return old(unit,op,...)
end
''')
        self.step();self.assertEqual(self.moves(),[])

    def test_support_rejection_defers_fallback_and_unknown_forget_not_replayed(self):
        self.lua.execute('''
TestWorld.forgetReads=0
BaiqiSettlementWarning.Read=function(_,_,index)
 if index==46 then return'KNOWN_NEGATIVE' end;return'NOT_APPLICABLE'
end
ExposedMembers.BaiqiSettlerGoalsBridge.Forget=function()
 TestWorld.forgetReads=TestWorld.forgetReads+1;return'UNAVAILABLE'
end
''')
        self.step();self.assertEqual(self.w.hintReads,0);self.assertEqual(self.moves(),[])
        self.step();self.assertEqual(self.w.hintReads,1);self.assertEqual(self.w.forgetReads,1)
        self.assertEqual(self.moves(),[(2,2,4)])


if __name__=='__main__':unittest.main()
