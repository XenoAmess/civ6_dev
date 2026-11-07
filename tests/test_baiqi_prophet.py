"""Prophet routing and earned qualification require native event plus real state."""
from pathlib import Path
import unittest
from lupa.lua51 import LuaRuntime
from prophet_intent_harness import install_prophet_bridge

ROOT = Path(__file__).resolve().parents[1]


class ProphetTests(unittest.TestCase):
    def setUp(self):
        self.lua = LuaRuntime(unpack_returned_tuples=True)
        for path in ('tests/lua/mock_world.lua', 'tests/lua/mock_scientist.lua', 'tests/lua/mock_prophet.lua',
                     'mod/Baiqi/Lua/BaiqiConfig.lua', 'mod/Baiqi/Lua/BaiqiPolicy.lua',
                     'mod/Baiqi/Lua/BaiqiPlanner.lua', 'mod/Baiqi/Lua/BaiqiController.lua'):
            if path.endswith('BaiqiController.lua'):
                install_prophet_bridge(self.lua)
            self.lua.execute((ROOT/path).read_text(encoding='utf-8'))
        self.w, self.c = self.lua.globals().TestWorld, self.lua.globals().BaiqiController
        self.logs = []
        self.lua.globals().print = lambda *args: self.logs.append(' '.join(map(str, args)))

    def found_requests(self):
        return [r for r in self.w.unitRequests.values() if r.op == 901]

    def observed(self):
        return [s for s in self.logs if 'kind=FOUND_RELIGION|proof=' in s]

    def test_zero_charge_prophet_walks_to_completed_site_then_uses_real_operation_once(self):
        self.c.RunNow()
        self.assertEqual(self.w.unitRequests[1].op, 10)
        self.w.scientistPlot = 43
        self.c.Update(0.35)
        self.assertEqual([r.op for r in self.w.unitRequests.values()], [10, 901])
        self.assertEqual(self.w.scientistCharges, 0)
        self.c.RunNow()
        self.assertEqual(len(self.found_requests()), 1)
        self.assertEqual(self.observed(), [])

    def test_consumption_and_actual_earned_state_alone_are_not_confirmation(self):
        self.w.scientistPlot = 43
        self.c.RunNow()
        self.w.withScientist, self.w.earnedBeliefs, self.w.foundingUnit = False, 2, False
        self.c.Update(3)
        self.assertEqual(self.observed(), [])
        self.w.strategic = False
        self.w.FireActivation(7, 4, 4, 70)  # A late native event still correlates while actions are gated.
        self.c.RunNow()
        self.assertEqual(self.observed(), [])
        self.w.strategic = True
        self.c.RunNow()
        self.assertEqual(len(self.observed()), 1)

    def test_matching_native_event_waits_for_actual_earned_qualification(self):
        self.w.scientistPlot = 43
        self.c.RunNow()
        self.w.FireActivation(7, 4, 4, 70)
        self.c.Update(3)
        self.assertEqual(self.observed(), [])
        self.w.earnedBeliefs = 2
        self.c.RunNow()
        self.assertEqual(self.observed(), [])
        self.w.foundingUnit, self.w.withScientist = False, False
        self.c.RunNow()
        self.assertEqual(len(self.observed()), 1)

    def test_wrong_event_player_full_id_class_and_individual_do_not_confirm(self):
        self.w.scientistPlot = 43
        self.c.RunNow()
        self.w.earnedBeliefs, self.w.foundingUnit, self.w.withScientist = 2, False, False
        for args in ((8, 4, 4, 70), (7, 65540, 4, 70), (7, 4, 5, 70), (7, 4, 4, 71)):
            self.w.FireActivation(*args)
        self.c.RunNow()
        self.assertEqual(self.observed(), [])

    def test_unknown_survives_turn_and_never_replays_or_spams(self):
        self.w.scientistPlot = 43
        self.c.RunNow()
        for _ in range(5):
            self.w.turn += 1
            self.c.Update(3)
        self.assertEqual(len(self.found_requests()), 1)
        self.assertEqual(sum('prophet_request_unresolved' in s for s in self.logs), 1)

    def test_incomplete_pillaged_hidden_or_foreign_sites_are_not_route_hints(self):
        for case in ('incomplete', 'pillaged', 'hidden', 'foreign'):
            with self.subTest(case=case):
                self.setUp()
                if case == 'incomplete':
                    self.w.completed = False
                elif case == 'pillaged':
                    self.w.pillaged = True
                elif case == 'hidden':
                    self.w.hiddenTarget = True
                else:
                    self.lua.execute('Map.GetPlotByIndex(43).GetOwner=function() return 8 end')
                self.c.RunNow()
                self.assertFalse(any(r.op in (10, 901) for r in self.w.unitRequests.values()))

    def test_qualification_formation_or_individual_change_during_native_check_blocks_request(self):
        for flag in ('changeQualification', 'changeFormation', 'changeIndividual'):
            with self.subTest(flag=flag):
                self.setUp()
                self.w.scientistPlot, self.w[flag] = 43, True
                self.c.RunNow()
                self.assertEqual(self.found_requests(), [])

    def test_already_earned_or_founded_or_native_rejected_cannot_found_again(self):
        for case in ('earned', 'founded', 'flag', 'reject'):
            with self.subTest(case=case):
                self.setUp()
                self.w.scientistPlot = 43
                if case == 'earned':
                    self.w.earnedBeliefs = 2
                elif case == 'founded':
                    self.w.createdReligion = 1
                elif case == 'flag':
                    self.w.foundingUnit = False
                else:
                    self.w.rejectFounding = True
                self.c.RunNow()
                self.assertEqual(self.found_requests(), [])

    def test_prophet_whitelist_does_not_allow_generic_activation_or_military_great_people(self):
        policy = self.lua.globals().BaiqiPolicy
        self.assertTrue(policy.ActionAllowed('UNIT_GREAT_PROPHET', 'FOUND_RELIGION'))
        self.assertFalse(policy.ActionAllowed('UNIT_GREAT_PROPHET', 'ACTIVATE_GREAT_PERSON'))
        for unit in ('UNIT_GREAT_GENERAL', 'UNIT_GREAT_ADMIRAL', 'UNIT_SETTLER'):
            self.assertFalse(policy.ActionAllowed(unit, 'FOUND_RELIGION'))

    def test_second_prophet_cannot_compete_with_unresolved_founding_request(self):
        self.w.scientistPlot = 43
        self.lua.execute('''
local w=TestWorld;local player=w.objects.player
local unit=player:GetUnits():FindID(4)
local second=setmetatable({GetID=function() return 7 end},{__index=unit})
player.GetUnits=function() return {Members=function() return ipairs({unit,second}) end,
 FindID=function(_,id) if id==4 then return unit elseif id==7 then return second end end} end
local can=UnitManager.CanStartOperation;w.secondaryFoundChecks=0
UnitManager.CanStartOperation=function(u,op,...)
 if u:GetID()==7 and op==901 then w.secondaryFoundChecks=w.secondaryFoundChecks+1 end
 return can(u,op,...)
end
local request=UnitManager.RequestOperation
UnitManager.RequestOperation=function(u,op,...)
 if u:GetID()==7 then
  assert(op==UnitOperationTypes.SKIP_TURN)
  table.insert(w.unitRequests,{unit=7,op=op,params=(...)})
 else return request(u,op,...) end
end
''')
        self.c.RunNow(); self.c.RunNow()
        self.assertEqual(len(self.found_requests()), 1)
        self.assertEqual(self.w.secondaryFoundChecks, 0)
        self.assertEqual(self.w.unitRequests[2].op, 17)
        self.assertNotIn('脚本错误', self.c.GetStatus())


    def test_unknown_prophet_request_not_replayed_after_controller_recreation(self):
        self.w.scientistPlot = 43
        self.c.RunNow()
        self.assertEqual(len(self.found_requests()), 1)
        self.lua.execute((ROOT / 'mod/Baiqi/Lua/BaiqiController.lua').read_text(encoding='utf-8'))
        self.c = self.lua.globals().BaiqiController
        self.c.RunNow()
        self.assertEqual(len(self.found_requests()), 1)

    def test_late_native_event_after_controller_recreation_updates_durable_record(self):
        self.w.scientistPlot = 43
        self.c.RunNow()
        self.c.Shutdown()
        self.lua.execute((ROOT / 'mod/Baiqi/Lua/BaiqiController.lua').read_text(encoding='utf-8'))
        self.c = self.lua.globals().BaiqiController
        self.c.RunNow()
        self.w.withScientist, self.w.earnedBeliefs, self.w.foundingUnit = False, 2, False
        self.w.FireActivation(7, 4, 4, 70)
        bridge = self.lua.globals().ExposedMembers.BaiqiProphetIntentBridge
        self.assertEqual(bridge.Inspect(7, 4)[0], 'OBSERVED')
        self.assertEqual(len(self.found_requests()), 1)

    def test_changed_qualification_after_persisted_permission_blocks_native_dispatch(self):
        self.w.scientistPlot = 43
        self.lua.execute('TestPropBridge.afterWrite=function() TestWorld.earnedBeliefs=2 end')
        self.c.RunNow()
        self.assertEqual(self.found_requests(), [])
        bridge = self.lua.globals().ExposedMembers.BaiqiProphetIntentBridge
        self.assertEqual(bridge.Inspect(7, 4)[0], 'ARMED')
        self.c.RunNow()
        self.assertEqual(self.found_requests(), [])

    def test_removed_or_recycled_unit_after_persisted_permission_is_not_dispatched(self):
        for kind in ('removed','alias'):
            with self.subTest(kind=kind):
                self.setUp()
                self.w.scientistPlot=43
                if kind=='removed':
                    self.lua.execute('TestPropBridge.afterWrite=function() TestWorld.withScientist=false end')
                else:
                    self.lua.execute('TestPropBridge.afterWrite=function() TestWorld.scientistID=65540;TestWorld.findScientistAlias=true end')
                self.c.RunNow()
                self.assertEqual(self.found_requests(),[])
                self.assertNotIn('脚本错误',self.c.GetStatus())

    def test_lost_prophet_ownership_after_durable_grant_holds_armed_without_native_order(self):
        self.w.scientistPlot = 43
        self.lua.execute('TestPropBridge.afterWrite=function() TestWorld.foundingUnit=false end')
        self.c.RunNow()
        self.assertEqual(self.found_requests(), [])
        bridge = self.lua.globals().ExposedMembers.BaiqiProphetIntentBridge
        self.assertEqual(bridge.Inspect(7, 4)[0], 'ARMED')
        self.c.RunNow()
        self.assertEqual(self.found_requests(), [])

    def test_unknown_prophet_ownership_never_routes_or_founds(self):
        for value in (None, 1, 'true'):
            with self.subTest(value=value):
                self.setUp()
                self.w.foundingUnit = value
                self.c.RunNow()
                self.assertFalse(any(r.op in (10, 901) for r in self.w.unitRequests.values()))

    def test_other_live_prophet_does_not_hide_correlated_completion(self):
        self.w.scientistPlot = 43
        self.c.RunNow()
        self.assertEqual(len(self.found_requests()), 1)
        self.lua.execute('''
local w=TestWorld;local player=w.objects.player
local original=player:GetUnits();local first=original:FindID(4)
local second=setmetatable({GetID=function()return 7 end},{__index=first})
player.GetUnits=function()return{
  FindID=function(_,id)
    if id==7 then return second end
    if id==4 then return w.withScientist and first or nil end
    return original:FindID(id)
  end,
  Members=function()
    local members={second};if w.withScientist then members[#members+1]=first end
    return ipairs(members)
  end}end
''')
        self.w.withScientist, self.w.earnedBeliefs, self.w.foundingUnit = False, 2, True
        self.w.FireActivation(7, 4, 4, 70)
        self.c.RunNow()
        self.assertEqual(len(self.observed()), 1)
        self.assertEqual(len(self.found_requests()), 1)


if __name__ == '__main__':
    unittest.main()
