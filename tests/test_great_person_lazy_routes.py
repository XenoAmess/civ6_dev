"""Real Controller routing consumers: same target and authority, fewer native reads."""
from pathlib import Path
import unittest
from lupa.lua51 import LuaRuntime as Lua51
from lupa.lua53 import LuaRuntime as Lua53
from prophet_intent_harness import install_prophet_bridge
from creative_intent_harness import install_creative_bridge

ROOT=Path(__file__).resolve().parents[1]
CASES=[(engine,kind)for engine in(Lua51,Lua53)for kind in('prophet','creative')]

class GreatPersonLazyRoutesTests(unittest.TestCase):
    def world(self,engine,kind):
        lua=engine(unpack_returned_tuples=True)
        lua.globals().print=lambda *args:None
        for name in('mock_world','mock_scientist','mock_'+kind):
            lua.execute((ROOT/f'tests/lua/{name}.lua').read_text(encoding='utf-8'))
        w=lua.globals().TestWorld
        if kind=='creative':
            w.withScientist=False
            install_creative_bridge(lua)
            w.withScientist=True
        else:
            install_prophet_bridge(lua)
        lua.execute((ROOT/'tests/lua/mock_great_person_routes.lua').read_text(encoding='utf-8'))
        for name in('BaiqiConfig','BaiqiPolicy','BaiqiPlanner','BaiqiController'):
            lua.execute((ROOT/f'mod/Baiqi/Lua/{name}.lua').read_text(encoding='utf-8'))
        lua.globals().print=lambda *args:None
        return lua,w,lua.globals().BaiqiController

    def queries(self,w):
        return list(w.routeQueries.values())

    def moves(self,w):
        return [r for r in w.unitRequests.values()if r.op==10]

    def test_nearest_reachable_preserves_move_and_reads_only_that_route(self):
        for engine,kind in CASES:
            with self.subTest(engine=engine.__module__,kind=kind):
                lua,w,c=self.world(engine,kind);c.RunNow()
                moves=self.moves(w);self.assertEqual(len(moves),1)
                self.assertEqual((moves[0].params[14],moves[0].params[15]),(3,3))
                self.assertEqual(self.queries(w),[43])

    def test_unreachable_nearest_tries_next_in_distance_order(self):
        for engine,kind in CASES:
            with self.subTest(engine=engine.__module__,kind=kind):
                lua,w,c=self.world(engine,kind);w.routeBlocked[43]=True;c.RunNow()
                moves=self.moves(w);self.assertEqual(len(moves),1)
                self.assertEqual((moves[0].params[14],moves[0].params[15]),(2,4))
                self.assertEqual(self.queries(w),[43,44])

    def test_equal_distance_uses_lower_plot_index_before_reading_path(self):
        for engine,kind in CASES:
            with self.subTest(engine=engine.__module__,kind=kind):
                lua,w,c=self.world(engine,kind)
                lua.execute('TestWorld.SetRouteSites({{45,10,9},{44,2,7},{43,6,3}})')
                c.RunNow();self.assertEqual(len(self.moves(w)),1)
                self.assertEqual(self.queries(w),[43])

    def test_all_unreachable_checks_each_once_in_priority_order(self):
        for engine,kind in CASES:
            with self.subTest(engine=engine.__module__,kind=kind):
                lua,w,c=self.world(engine,kind)
                for index in(43,44,45):w.routeBlocked[index]=True
                c.RunNow();self.assertEqual(self.moves(w),[])
                self.assertEqual(self.queries(w),[43,44,45])

    def test_first_reachable_native_refusal_does_not_try_another_move(self):
        for engine,kind in CASES:
            with self.subTest(engine=engine.__module__,kind=kind):
                lua,w,c=self.world(engine,kind)
                lua.execute('''local old=UnitManager.CanStartOperation;TestWorld.routeMoveChecks={}
UnitManager.CanStartOperation=function(u,op,v,p)
 if op==10 then table.insert(TestWorld.routeMoveChecks,{p[14],p[15]});return false end
 return old(u,op,v,p)
end''')
                c.RunNow();self.assertEqual(self.moves(w),[])
                checks=list(w.routeMoveChecks.values());self.assertTrue(checks)
                self.assertTrue(all((r[1],r[2])==(3,3)for r in checks))

    def test_formation_change_at_native_eligibility_still_blocks_move(self):
        for engine,kind in CASES:
            with self.subTest(engine=engine.__module__,kind=kind):
                lua,w,c=self.world(engine,kind)
                lua.execute('''local old=UnitManager.CanStartOperation
UnitManager.CanStartOperation=function(u,op,...)
 local result=old(u,op,...);if op==10 then TestWorld.scientistFormation=2 end;return result
end''')
                c.RunNow();self.assertEqual(self.moves(w),[])

    def test_escorted_unit_never_starts_route_search(self):
        for engine,kind in CASES:
            with self.subTest(engine=engine.__module__,kind=kind):
                lua,w,c=self.world(engine,kind);w.scientistFormation=2;c.RunNow()
                self.assertEqual(self.queries(w),[]);self.assertEqual(self.moves(w),[])

    def test_current_site_activation_precedes_route_search(self):
        for engine,kind in CASES:
            with self.subTest(engine=engine.__module__,kind=kind):
                lua,w,c=self.world(engine,kind);w.scientistPlot=43;c.RunNow()
                self.assertEqual(self.queries(w),[])
                if kind=='prophet':
                    self.assertEqual(sum(r.op==901 for r in w.unitRequests.values()),1)
                else:
                    self.assertEqual(len(w.commandRequests),1)
