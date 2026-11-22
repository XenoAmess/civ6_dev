"""Exercise actual Controller waiting and recovery; these are software doubles."""
from pathlib import Path
import unittest

from lupa.lua51 import LuaRuntime as Lua51
from lupa.lua53 import LuaRuntime as Lua53

ROOT = Path(__file__).resolve().parents[1]


def world(vm, controller_source=None):
    lua = vm(unpack_returned_tuples=True)
    lua.execute((ROOT/'tests/lua/mock_world.lua').read_text(encoding='utf-8'))
    for name in ('BaiqiConfig', 'BaiqiPolicy', 'BaiqiPlanner'):
        lua.execute((ROOT/f'mod/Baiqi/Lua/{name}.lua').read_text(encoding='utf-8'))
    lua.execute(controller_source if controller_source is not None else
                (ROOT/'mod/Baiqi/Lua/BaiqiController.lua').read_text(encoding='utf-8'))
    lua.execute('''
TestWorld.rejectProduction=true;TestWorld.qualificationCalls=0;TestWorld.waitLogs=0
local original=CityManager.CanStartOperation
CityManager.CanStartOperation=function(...)
 TestWorld.qualificationCalls=TestWorld.qualificationCalls+1
 if TestWorld.rejectProduction then return false end
 return original(...)
end
local originalPrint=print
print=function(...)
 local first=(...)
 if type(first)=='string' and string.find(first,'BAIQI|wait|',1,true)
   and string.find(first,'key=city:66|',1,true)then TestWorld.waitLogs=TestWorld.waitLogs+1 end
 return originalPrint(...)
end
''')
    return lua, lua.globals().TestWorld, lua.globals().BaiqiController


class NoCandidateRetryTests(unittest.TestCase):
    def each(self):
        for name, vm in [('Lua51', Lua51), ('Lua53', Lua53)]:
            yield name, world(vm)

    def test_same_turn_restores_without_event_refresh_or_forced_end(self):
        for name, (lua, w, c) in self.each():
            with self.subTest(VM=name):
                c.RunNow()
                initial = w.qualificationCalls
                self.assertGreater(initial, 0)
                self.assertEqual(len(w.cityRequests), 0)
                w.rejectProduction = False
                for _ in range(50):
                    c.RunNow()
                self.assertEqual(w.qualificationCalls, initial)
                c.Update(9.9)
                self.assertEqual(len(w.cityRequests), 0)
                c.Update(0.5)
                self.assertEqual(len(w.cityRequests), 1, c.GetStatus())
                self.assertEqual(w.cityRequests[1][2], 101)
                self.assertEqual(w.turn, 1)
                self.assertEqual(len(w.unitRequests), 0)
                self.assertEqual(w.waitLogs, 1)

    def test_ongoing_refusal_has_finite_scans_no_requests_and_one_reason(self):
        for name, (lua, w, c) in self.each():
            with self.subTest(VM=name):
                c.RunNow()
                initial = w.qualificationCalls
                for _ in range(200):
                    c.RunNow()
                self.assertEqual(w.qualificationCalls, initial)
                c.Update(9.9)
                self.assertEqual(w.qualificationCalls, initial)
                c.Update(0.5)
                self.assertEqual(w.qualificationCalls, 2*initial)
                c.Update(100)  # One reconsideration, without catch-up scans.
                self.assertEqual(w.qualificationCalls, 3*initial)
                self.assertEqual(len(w.cityRequests), 0)
                self.assertEqual(len(w.unitRequests), 0)
                self.assertEqual(w.waitLogs, 1)

    def test_disabled_updates_do_not_advance_reconsideration_clock(self):
        for name, (lua, w, c) in self.each():
            with self.subTest(VM=name):
                c.RunNow()
                initial = w.qualificationCalls
                w.rejectProduction = False
                c.Update(100, False)
                c.RunNow()
                self.assertEqual(w.qualificationCalls, initial)
                c.Update(9.9)
                self.assertEqual(len(w.cityRequests), 0)
                c.Update(0.5)
                self.assertEqual(len(w.cityRequests), 1)

    def test_new_nonempty_queue_is_preserved_when_delay_expires(self):
        for name, (lua, w, c) in self.each():
            with self.subTest(VM=name):
                c.RunNow()
                initial = w.qualificationCalls
                w.rejectProduction, w.queueSize = False, 2
                c.Update(11)
                c.Update(100)
                self.assertEqual(w.qualificationCalls, initial)
                self.assertEqual(w.queueSize, 2)
                self.assertEqual(len(w.cityRequests), 0)

    def test_inactive_updates_do_not_age_a_same_turn_refusal(self):
        for name, (lua, w, c) in self.each():
            with self.subTest(VM=name):
                c.RunNow()
                initial = w.qualificationCalls
                w.rejectProduction, w.strategic = False, False
                c.Update(100)
                w.strategic = True
                c.RunNow()
                self.assertEqual(w.qualificationCalls, initial)
                c.Update(11)
                self.assertEqual(len(w.cityRequests), 1)

    def test_new_turn_reconsiders_without_inheriting_prior_deadline(self):
        for name, (lua, w, c) in self.each():
            with self.subTest(VM=name):
                c.RunNow()
                w.rejectProduction, w.turn = False, 2
                c.RunNow()
                self.assertEqual(len(w.cityRequests), 1)
                self.assertEqual(w.cityRequests[1][2], 101)

    def test_explicit_refresh_preserves_same_turn_attempts(self):
        for name, (lua, w, c) in self.each():
            with self.subTest(VM=name):
                c.RunNow()
                w.rejectProduction = False
                c.Update(11)
                self.assertEqual(len(w.cityRequests), 1)
                for _ in range(20):
                    c.RefreshProduction()
                    c.RunNow()
                self.assertEqual(len(w.cityRequests), 1)
                self.assertEqual(w.turn, 1)


if __name__ == '__main__':
    unittest.main()
