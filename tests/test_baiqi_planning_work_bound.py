"""Bound native city probes and keep restored movement proposals read only."""
from pathlib import Path
import unittest
from lupa.lua53 import LuaRuntime
import test_baiqi_settler_direct_goal as direct

ROOT=Path(__file__).resolve().parents[1]


class RetainedProposalWorkTests(unittest.TestCase):
    candidate_source=None
    setUp=direct.DirectSettlerGoalTests.setUp
    step=direct.DirectSettlerGoalTests.step
    moves=direct.DirectSettlerGoalTests.moves

    def spy_remember(self):
        self.lua.execute('''
TestWorld.rememberCalls=0
local prior=ExposedMembers.BaiqiSettlerGoalsBridge.Remember
ExposedMembers.BaiqiSettlerGoalsBridge.Remember=function(...)
 TestWorld.rememberCalls=TestWorld.rememberCalls+1;return prior(...)
end
''')

    def test_confirmed_restored_goal_moves_without_repeated_remember(self):
        self.spy_remember();self.step()
        self.assertEqual(self.moves(),[(2,3,3)])
        self.assertEqual(self.w.rememberCalls,0)
        self.assertEqual(self.w.goalProposals['2'].plot,46)

    def test_goal_changed_during_path_is_not_overwritten_or_followed(self):
        self.spy_remember()
        self.lua.execute('''
local prior=UnitManager.GetMoveToPathEx
UnitManager.GetMoveToPathEx=function(unit,index)
 local path=prior(unit,index)
 TestWorld.goalProposals['2']={unitID=2,unitType='UNIT_SETTLER',plot=47,x=8,y=4}
 return path
end
''')
        self.step();self.assertEqual(self.moves(),[])
        self.assertEqual(self.w.goalProposals['2'].plot,47)
        self.assertEqual(self.w.rememberCalls,0)

    def test_missing_fresh_goal_blocks_move_without_recreating_it(self):
        self.spy_remember()
        self.lua.execute('''
local prior=ExposedMembers.BaiqiSettlerGoalsBridge.Read;local n=0
ExposedMembers.BaiqiSettlerGoalsBridge.Read=function(...)
 n=n+1;if n>1 then return 'UNAVAILABLE' end;return prior(...)
end
''')
        self.step();self.assertEqual(self.moves(),[])
        self.assertEqual(self.w.rememberCalls,0)

    def test_malformed_fresh_goal_never_authorizes_a_move(self):
        self.spy_remember()
        self.lua.execute('''
local prior=ExposedMembers.BaiqiSettlerGoalsBridge.Read;local n=0
ExposedMembers.BaiqiSettlerGoalsBridge.Read=function(...)
 n=n+1
 if n>1 then return 'READY',{unitID=4,unitType='UNIT_SETTLER',plot=46,x=8,y=3} end
 return prior(...)
end
''')
        self.step();self.assertEqual(self.moves(),[])
        self.assertEqual(self.w.rememberCalls,0)

    def test_unpersisted_local_proposal_still_remembers_before_moving(self):
        self.step();self.w.settlerPlot,self.w.turn=43,2
        self.lua.execute("TestWorld.goalProposals['2']=nil;TestWorld.paths[46]={43,60,61,62,48,46}")
        self.spy_remember();self.step()
        self.assertEqual(self.w.rememberCalls,1)
        self.assertEqual(self.w.goalProposals['2'].plot,46)
        self.assertEqual(self.moves(),[(2,3,3),(2,4,3)])


class CityProbeWorkTests(unittest.TestCase):
    def setUp(self):
        self.lua=LuaRuntime(unpack_returned_tuples=True)
        self.lua.execute((ROOT/'tests/lua/mock_world.lua').read_text(encoding='utf-8'))
        self.lua.execute('''
local w=TestWorld;local original=w.objects.city;local q=original:GetBuildQueue()
w.withBuilder=false;w.withSettler=false;w.cityProbeIDs={};w.manyCities={}
w.newProbeCity=function(id)
 local city=setmetatable({},{__index=original})
 city.GetID=function()return id end
 local queue=setmetatable({},{__index=q})
 queue.GetSize=function()w.cityProbeIDs[id]=true;return 1 end
 city.GetBuildQueue=function()return queue end
 return city
end
for i=1,10 do w.manyCities[i]=w.newProbeCity(100+i)end
w.objects.player.GetCities=function()
 return{GetCount=function()return#w.manyCities end,
  Members=function()return ipairs(w.manyCities)end,
  FindID=function(_,id)for _,city in ipairs(w.manyCities)do if city:GetID()==id then return city end end end}
end
''')
        for name in('BaiqiConfig','BaiqiPolicy','BaiqiPlanner','BaiqiController'):
            self.lua.execute((ROOT/f'mod/Baiqi/Lua/{name}.lua').read_text(encoding='utf-8'))
        self.w=self.lua.globals().TestWorld;self.c=self.lua.globals().BaiqiController

    def step(self):
        self.lua.execute('TestWorld.cityProbeIDs={}')
        self.c.RunNow();self.assertNotIn('脚本错误',self.c.GetStatus())
        return set(self.w.cityProbeIDs.keys())

    def test_each_callback_probes_one_busy_city_and_all_ten_make_progress(self):
        visited=set()
        for _ in range(10):
            ids=self.step();self.assertEqual(len(ids),1);visited.update(ids)
        self.assertEqual(visited,set(range(101,111)))
        self.assertEqual(len(self.w.cityRequests),0)
        self.assertEqual(len(self.w.unitRequests),0)

    def test_membership_change_preserves_bounded_fairness(self):
        for _ in range(3):self.step()
        self.lua.execute('table.remove(TestWorld.manyCities,1);table.remove(TestWorld.manyCities,1);table.insert(TestWorld.manyCities,TestWorld.newProbeCity(211))')
        visited=set()
        for _ in range(9):
            ids=self.step();self.assertEqual(len(ids),1);visited.update(ids)
        self.assertEqual(visited,{*range(103,111),211})
        self.assertEqual(len(self.w.cityRequests),0)

    def test_passive_callback_does_not_probe_city_queues(self):
        self.c.RunNow(False)
        self.assertEqual(set(self.w.cityProbeIDs.keys()),set())
        self.assertEqual(len(self.step()),1)

    def test_busy_cities_do_not_starve_an_idle_civilian(self):
        self.w.withBuilder=True
        self.assertEqual(len(self.step()),1)
        self.assertEqual([(r.unit,r.op)for r in self.w.unitRequests.values()],[(3,17)])

    def test_member_traversal_still_progresses_when_count_reader_is_unavailable(self):
        self.lua.execute('''
local prior=TestWorld.objects.player.GetCities
TestWorld.objects.player.GetCities=function(...)
 local cities=prior(...);cities.GetCount=function()return nil end;return cities
end
''')
        visited=set()
        for _ in range(10):
            ids=self.step();self.assertEqual(len(ids),1);visited.update(ids)
        self.assertEqual(visited,set(range(101,111)))


if __name__=='__main__':unittest.main()
