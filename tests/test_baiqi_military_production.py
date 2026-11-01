"""Useful military production respects native legality and in-flight commitments."""
from pathlib import Path
import unittest
from lupa.lua53 import LuaRuntime

ROOT = Path(__file__).resolve().parents[1]


class BaiqiMilitaryProductionTests(unittest.TestCase):
    def setUp(self):
        self.lua = LuaRuntime(unpack_returned_tuples=True)
        for name in ('tests/lua/mock_world.lua', 'tests/lua/mock_trade.lua', 'tests/lua/mock_military.lua',
                     'mod/Baiqi/Lua/BaiqiConfig.lua', 'mod/Baiqi/Lua/BaiqiPolicy.lua',
                     'mod/Baiqi/Lua/BaiqiPlanner.lua', 'mod/Baiqi/Lua/BaiqiController.lua'):
            self.lua.execute((ROOT/name).read_text(encoding='utf-8'))
        self.w = self.lua.globals().TestWorld
        self.c = self.lua.globals().BaiqiController

    def units(self):
        return [r.params[4] for r in self.w.cityRequests.values() if r.params[4] is not None]

    def test_same_tick_pending_commitment_balances_melee_and_ranged_without_army_orders(self):
        self.c.RunNow()
        self.c.RunNow()
        self.assertEqual(self.units(), [206, 205])
        self.assertEqual(len(self.w.unitRequests), 0)

    def test_existing_recon_cap_uses_project_when_only_scout_training_is_available(self):
        self.lua.execute('TestWorld.armyTypes={0};TestWorld.allowedMilitary={[200]=true};TestWorld.allowProject=true')
        self.c.RunNow()
        self.assertEqual(self.units(), [])
        self.assertEqual(self.w.cityRequests[1].params[5], 301)
        self.assertEqual(len(self.w.unitRequests), 0)

    def test_empty_queue_pending_recon_reserves_capacity_before_native_ack(self):
        self.lua.execute('TestWorld.allowedMilitary={[200]=true};TestWorld.allowProject=true')
        self.c.RunNow()
        self.c.RunNow()
        self.assertEqual(self.units(), [200])
        self.assertEqual(self.w.cityRequests[2].params[5], 301)

    def test_native_queued_recon_and_acknowledged_pending_are_counted_once(self):
        self.lua.execute('TestWorld.cityCount=8;TestWorld.allowedMilitary={[200]=true}')
        self.c.RunNow()
        self.lua.execute('TestWorld.queues[66]={{UnitType=0}}')
        self.c.RunNow()
        self.assertEqual(self.units(), [200, 200])
        self.w.turn += 1
        self.lua.execute('TestWorld.queues[67]={{UnitType=0}}')
        self.c.RunNow()
        self.assertEqual(self.units(), [200, 200])

    def test_stronger_legal_frontline_wins_and_engine_rejection_preserves_fallback(self):
        self.w.allowedMilitary[207] = True
        self.c.RunNow()
        self.assertEqual(self.units(), [207])
        self.setUp()
        self.w.allowedMilitary[207], self.w.rejectMilitaryHash = True, 207
        self.c.RunNow()
        self.assertEqual(self.units(), [206])

    def test_existing_and_queued_frontline_deficit_selects_ranged(self):
        self.lua.execute('TestWorld.armyTypes={6};TestWorld.queues[66]={{UnitType=6}}')
        self.c.RunNow()
        self.assertEqual(self.units(), [205])

    def test_support_naval_and_siege_do_not_displace_available_frontline_or_campus(self):
        self.lua.execute('for _,h in ipairs({208,209,210}) do TestWorld.allowedMilitary[h]=true end')
        self.c.RunNow()
        self.assertEqual(self.units(), [206])
        self.lua.execute('''
local roles={recon=0,frontline=0,ranged=0,siege=0,support=0,naval=0,air=0}
local score=BaiqiPlanner.MilitaryScore({Combat=1000000}, {cities=2,militaryRoles=roles},BaiqiConfig)
local chosen=BaiqiPlanner.Choose({paused=false,queueEmpty=true},
 {{index=0,score=score,legal=true,type='army'},{index=99,score=68,legal=true,type='campus'}})
assert(chosen.type=='campus')
''')

    def test_active_settler_hash_without_visible_queue_entry_reserves_capacity(self):
        self.lua.execute('''
TestWorld.EnableSettlerSite()
TestWorld.allowedMilitary={[201]=true};TestWorld.allowProject=true
local original=TestWorld.objects.city.GetBuildQueue
TestWorld.objects.city.GetBuildQueue=function(city)
 local q=original(city)
 if city:GetID()==66 then q.GetCurrentProductionTypeHash=function() return 201 end end
 return q
end
''')
        self.c.RunNow()
        self.assertEqual(self.units(), [])
        self.assertEqual(self.w.cityRequests[1].city, 67)
        self.assertEqual(self.w.cityRequests[1].params[5], 301)

    def test_settler_budget_is_rechecked_after_native_candidate_validation(self):
        self.lua.execute('''
TestWorld.EnableSettlerSite();TestWorld.allowedMilitary={[201]=true};TestWorld.allowProject=true
local checks=0
CityManager.CanStartOperation=function(city,operation,params)
 if params[CityOperationTypes.PARAM_UNIT_TYPE]==201 then
  checks=checks+1
  if checks==2 then TestWorld.queues[67]={{UnitType=1}} end
 end
 return true
end
''')
        self.c.RunNow()
        self.assertEqual(self.units(), [])
        self.assertEqual(len(self.w.cityRequests), 0)
        self.c.RunNow()
        self.assertEqual(self.units(), [])
        self.assertEqual(self.w.cityRequests[1].city, 66)
        self.assertEqual(self.w.cityRequests[1].params[5], 301)

    def test_acknowledged_settler_commitment_survives_same_turn_stale_project_view(self):
        self.lua.execute('''
TestWorld.EnableSettlerSite()
TestWorld.allowedMilitary={[201]=true};TestWorld.allowProject=true
TestWorld.blockSecondCity=true
''')
        self.c.RunNow()
        self.assertEqual(self.units(), [201])
        self.lua.execute('TestWorld.queues[66]={{UnitType=1}}')
        self.c.RunNow()  # Observe the actual accepted unit entry.
        self.lua.execute('TestWorld.queues[66]={{ProjectType=0}};TestWorld.blockSecondCity=false')
        self.c.RefreshProduction()
        self.c.RunNow()
        self.assertEqual(self.units(), [201])
        self.assertEqual(self.w.cityRequests[2].params[5], 301)

    def test_unresolved_settler_reservation_is_not_lost_when_other_hash_appears(self):
        self.lua.execute('''
TestWorld.EnableSettlerSite()
TestWorld.allowedMilitary={[201]=true};TestWorld.allowProject=true
TestWorld.blockSecondCity=true
''')
        self.c.RunNow()
        # No accepted settler entry: a different view appears before its outcome.
        self.lua.execute('TestWorld.queues[66]={{ProjectType=0}};TestWorld.blockSecondCity=false')
        self.c.RefreshProduction()
        self.c.RunNow()
        self.assertEqual(self.units(), [201])

    def test_same_settler_queue_hash_and_submitted_commitment_are_counted_once(self):
        self.lua.execute('''
TestWorld.EnableSettlerSite()
TestWorld.allowedMilitary={[201]=true};TestWorld.allowProject=true
TestWorld.blockSecondCity=true;BaiqiConfig.maxSettlers=2
''')
        self.c.RunNow()
        self.lua.execute('TestWorld.queues[66]={{UnitType=1}};TestWorld.blockSecondCity=false')
        self.c.RefreshProduction()
        self.c.RunNow()
        self.assertEqual(self.units(), [201, 201])

    def test_next_turn_recomputes_completed_settler_commitment_from_actual_objects(self):
        self.lua.execute('''
TestWorld.EnableSettlerSite()
TestWorld.allowedMilitary={[201]=true};TestWorld.allowProject=true
TestWorld.blockSecondCity=true
''')
        self.c.RunNow()
        self.lua.execute('TestWorld.queues[66]={{UnitType=1}}')
        self.c.RunNow()
        # Next-turn fixture: original unit is no longer queued or alive.
        self.lua.execute('TestWorld.turn=2;TestWorld.queues[66]={{ProjectType=0}};TestWorld.blockSecondCity=false')
        self.c.RunNow()
        self.assertEqual(self.units(), [201, 201])


if __name__ == '__main__':
    unittest.main()
