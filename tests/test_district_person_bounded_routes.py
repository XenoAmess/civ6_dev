"""Real Tick consumer resumes district-person negative probes, both Lua engines."""
import unittest
from unittest.mock import patch
from lupa.lua51 import LuaRuntime as Lua51
from lupa.lua53 import LuaRuntime as Lua53
import test_baiqi_scientist as scientist
import test_baiqi_gp_paths as paths_fixture
import test_baiqi_neutral_people as border_fixture


class BoundedDistrictRoutesTests(unittest.TestCase):
    def worlds(self, fixture_type=paths_fixture.GreatPersonPathTests):
        result = []
        for runtime in (Lua51, Lua53):
            f = fixture_type()
            with patch.object(scientist, 'LuaRuntime', runtime):
                f.setUp()
            result.append(f)
        return result

    def test_two_failed_probes_resume_without_standby_then_reach_third(self):
        for f in self.worlds():
            f.lua.execute('TestWorld.blocked={[43]=true,[44]=true}')
            for paths in ([43], [43, 44]):
                f.c.RunNow()
                self.assertEqual(f.paths(), paths)
                self.assertEqual(len(f.w.unitRequests), 0)
            f.c.RunNow()
            self.assertEqual(f.paths(), [43, 44, 45])
            self.assertEqual([r.op for r in f.w.unitRequests.values()], [10])

    def test_last_failure_exhausts_and_does_not_busy_loop(self):
        for f in self.worlds():
            f.lua.execute('TestWorld.blocked={[43]=true,[44]=true,[45]=true}')
            for count in (1, 2, 3):
                f.c.RunNow()
                self.assertEqual(len(f.w.pathRequests), count)
                self.assertEqual(len(f.w.unitRequests), int(count == 3))
            for _ in range(5):
                f.c.RunNow()
            self.assertEqual(f.paths(), [43, 44, 45])
            self.assertEqual([r.op for r in f.w.unitRequests.values()], [17])

    def test_retained_destination_failure_uses_only_one_probe(self):
        for f in self.worlds():
            f.lua.execute('TestWorld.targets={42,45};TestWorld.steps[45]=43')
            f.c.RunNow()
            f.w.scientistPlot = 43
            f.lua.execute('TestWorld.targets={42,44,45};TestWorld.blocked[45]=true')
            f.c.RunNow()
            self.assertEqual(f.paths(), [45, 45])
            self.assertEqual(len(f.w.unitRequests), 1)
            f.c.RunNow()
            self.assertEqual(f.paths(), [45, 45, 44])
            self.assertEqual(len(f.w.unitRequests), 2)

    def test_fresh_owner_reveal_and_formation_rechecked_at_resume(self):
        for change in ('TestWorld.scientistOwner=8', 'TestWorld.scientistFormation=2',
                       'TestWorld.scientistFormation=nil',
                       'TestWorld.scientistCharges=0', 'TestWorld.scientistReady=false',
                       'TestWorld.hidden[44]=true;TestWorld.hidden[45]=true',
                       'TestWorld.foreign=44;TestWorld.hidden[45]=true'):
            for f in self.worlds():
                with self.subTest(change=change):
                    f.lua.execute('TestWorld.blocked[43]=true')
                    f.c.RunNow()
                    self.assertEqual(f.paths(), [43])
                    f.lua.execute(change)
                    f.c.RunNow()
                    self.assertEqual(f.paths(), [43])
                    self.assertFalse(any(r.op == 10 for r in f.w.unitRequests.values()))

    def test_new_charge_or_individual_restarts_fresh_negative_wave(self):
        for change in ('TestWorld.scientistCharges=2',
                       "GameInfo.GreatPersonIndividuals[71]={Index=71,GreatPersonClassType='GREAT_PERSON_CLASS_SCIENTIST',ActionRequiresCompletedDistrictType='DISTRICT_CAMPUS'};TestWorld.scientistIndividual=71"):
            for f in self.worlds():
                f.lua.execute('TestWorld.blocked[43]=true')
                f.c.RunNow()
                self.assertEqual(f.paths(), [43])
                f.lua.execute(change)
                f.c.RunNow()
                self.assertEqual(f.paths(), [43, 43])
                self.assertEqual(len(f.w.unitRequests), 0)

    def test_later_turn_refreshes_route_negatives(self):
        for f in self.worlds():
            f.lua.execute('TestWorld.blocked[43]=true')
            f.c.RunNow()
            f.w.turn += 1
            f.lua.execute('TestWorld.blocked={}')
            f.c.RunNow()
            self.assertEqual(f.paths(), [43, 43])
            self.assertEqual([r.op for r in f.w.unitRequests.values()], [10])

    def test_held_intent_between_probes_prevents_resume_and_fallback(self):
        for f in self.worlds():
            f.lua.execute('TestWorld.blocked[43]=true')
            f.c.RunNow()
            f.w.scientistPlot = 43
            granted, _, _ = f.lua.globals().ExposedMembers.BaiqiGreatPersonIntentBridge.Prepare(
                7, 4, 'UNIT_GREAT_SCIENTIST', 5, 70, 1, 3, 3)
            self.assertTrue(granted)
            f.w.scientistPlot = 42
            f.c.RunNow()
            self.assertEqual(f.paths(), [43])
            self.assertEqual(len(f.w.unitRequests), 0)

    def test_current_activation_and_first_reachable_refusal_still_win(self):
        for f in self.worlds():
            f.lua.execute('TestWorld.blocked[43]=true')
            f.c.RunNow()
            f.w.scientistPlot = 44
            f.lua.execute('TestWorld.legal[44]=true')
            f.c.RunNow()
            self.assertEqual(f.paths(), [43])
            self.assertEqual(len(f.w.commandRequests), 1)
        for f in self.worlds():
            f.lua.execute('TestWorld.blocked[43]=true;TestWorld.rejectMove=true')
            f.c.RunNow()
            f.c.RunNow()
            self.assertEqual(f.paths(), [43, 44])
            self.assertEqual([r.op for r in f.w.unitRequests.values()], [17])
            f.c.RunNow()
            self.assertEqual(f.paths(), [43, 44])

    def test_city_planning_runs_before_the_next_route_probe(self):
        for f in self.worlds():
            f.lua.execute('TestWorld.blocked[43]=true')
            f.c.RunNow()
            self.assertEqual(f.paths(), [43])
            f.lua.execute('''
local city=TestWorld.objects.city;local original=city.GetBuildQueue
TestWorld.queueReads=0
city.GetBuildQueue=function(...)TestWorld.queueReads=TestWorld.queueReads+1;return original(...)end
''')
            f.c.RefreshProduction()
            f.c.RunNow()
            self.assertGreater(f.w.queueReads, 0)
            self.assertEqual(f.paths(), [43,44])

    def test_retained_border_failure_continues_without_a_second_path(self):
        for f in self.worlds(border_fixture.NeutralGreatPersonTests):
            f.w.noPath = 43
            f.c.RunNow()
            self.assertEqual(list(f.w.paths.values()), [43])
            self.assertEqual(len(f.w.unitRequests), 0)
            f.c.RunNow()
            self.assertEqual(list(f.w.paths.values()), [43, 45])
            f.w.scientistPlot = 46
            f.w.noPath = 45
            f.w.turn += 1
            f.c.RunNow()
            self.assertEqual(list(f.w.paths.values()), [43, 45, 45])
            self.assertEqual(len(f.w.unitRequests), 1)
            f.c.RunNow()
            self.assertEqual(list(f.w.paths.values()), [43, 45, 45, 43])
            self.assertEqual(len(f.w.unitRequests), 2)

    def test_border_last_failed_target_exhausts_without_busy_continuation(self):
        for f in self.worlds(border_fixture.NeutralGreatPersonTests):
            f.w.owners[45] = 8
            f.w.noPath = 43
            f.c.RunNow()
            self.assertEqual(list(f.w.paths.values()), [43])
            self.assertEqual([r.op for r in f.w.unitRequests.values()], [17])
            for _ in range(4):
                f.c.RunNow()
            self.assertEqual(list(f.w.paths.values()), [43])
