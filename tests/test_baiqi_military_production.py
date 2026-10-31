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


if __name__ == '__main__':
    unittest.main()
