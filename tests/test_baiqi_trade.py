"""Actual controller packets meet delayed trade and production consumers."""
from pathlib import Path
import unittest
from lupa.lua53 import LuaRuntime

ROOT = Path(__file__).resolve().parents[1]


class BaiqiTradeTests(unittest.TestCase):
    def setUp(self):
        self.lua = LuaRuntime(unpack_returned_tuples=True)
        for p in ('tests/lua/mock_world.lua', 'tests/lua/mock_trade.lua',
                  'mod/Baiqi/Lua/BaiqiConfig.lua', 'mod/Baiqi/Lua/BaiqiPolicy.lua',
                  'mod/Baiqi/Lua/BaiqiPlanner.lua', 'mod/Baiqi/Lua/BaiqiController.lua'):
            self.lua.execute((ROOT / p).read_text(encoding='utf-8'))
        self.w = self.lua.globals().TestWorld
        self.c = self.lua.globals().BaiqiController

    def test_domestic_packet_waits_for_matching_actual_route_without_movement(self):
        self.c.RunNow()
        self.assertEqual(len(self.w.unitRequests), 1, self.c.GetStatus())
        r = self.w.unitRequests[1]
        self.assertEqual((r.unit, r.op, r.params.x0, r.params.y0, r.params.x1, r.params.y1),
                         (4, 18, 3, 3, 2, 3))
        self.w.busy = True
        self.c.Update(2)
        self.assertEqual(len(self.w.unitRequests), 1)
        # The independent consumer confirms the real trader and destination.
        self.lua.execute('TestWorld.routes={{TraderUnitID=4,DestinationCityPlayer=7,DestinationCityID=67}}')
        self.w.activeRoutes, self.w.activity, self.w.busy = 1, 200, False
        self.c.Update(0.35)
        self.w.turn += 1
        self.c.RunNow()
        self.assertEqual((len(self.w.unitRequests), self.w.traderPlot, self.w.traderMoves), (1, 42, 2))

    def test_pending_capacity_is_reserved_and_wrong_trader_cannot_confirm(self):
        self.w.secondTrader = True
        self.c.RunNow()
        self.lua.execute('TestWorld.routes={{TraderUnitID=99,DestinationCityPlayer=7,DestinationCityID=67}}')
        self.w.busy = True
        self.c.Update(0.35)
        self.assertEqual([self.w.unitRequests[i].op for i in range(1, len(self.w.unitRequests)+1)], [18, 17])

    def test_native_idle_rejection_waits_without_same_turn_replay_and_replans_next_turn(self):
        self.c.RunNow()
        self.c.Update(0.35)
        self.assertEqual(len(self.w.unitRequests), 1)
        self.c.Update(0.35)
        self.assertEqual((len(self.w.unitRequests), self.w.unitRequests[2].op), (2, 17))
        self.c.Update(3)
        self.assertEqual(len(self.w.unitRequests), 2)
        self.w.turn += 1
        self.c.RunNow()
        self.assertEqual(self.w.unitRequests[3].op, 18)

    def test_active_or_escorted_traders_receive_no_commands(self):
        self.w.tradeFormation = 2
        self.c.RunNow()
        self.assertEqual(len(self.w.unitRequests), 0)
        self.w.tradeFormation, self.w.activity = 1, 200
        self.w.turn += 1
        self.c.RunNow()
        self.assertEqual(len(self.w.unitRequests), 0)

    def test_capacity_native_rejection_visibility_foreign_and_threat_only_allow_wait(self):
        for flag, value in (('tradeCapacity', 0), ('nativeReject', True), ('pathHidden', True),
                            ('pathForeign', True), ('destForeign', True), ('enemy', True)):
            with self.subTest(flag=flag):
                self.setUp()
                self.w[flag] = value
                self.c.RunNow()
                self.assertEqual((len(self.w.unitRequests), self.w.unitRequests[1].op), (1, 17))
        self.setUp()
        self.w.fogged, self.w.enemy = True, True
        self.c.RunNow()
        self.assertEqual(self.w.unitVisibilityReads or 0, 0)
        self.assertEqual(self.w.unitRequests[1].op, 18)

    def test_normal_production_counts_actual_and_queued_traders(self):
        self.w.withTrader, self.w.productionMode = False, True
        self.c.RunNow()
        self.assertEqual(len(self.w.cityRequests), 1, self.c.GetStatus())
        packet = self.w.cityRequests[1]
        self.assertEqual((packet.op, packet.params[4]), (1, 203))
        self.lua.execute('TestWorld.queues[66]={{UnitType="UNIT_TRADER"}}')
        self.c.RunNow()
        self.assertEqual(len(self.w.cityRequests), 1)
        self.lua.execute('TestWorld.queues[66]={}')
        self.w.withTrader, self.w.turn = True, self.w.turn+1
        self.c.RunNow()
        self.assertEqual(len(self.w.cityRequests), 1)


if __name__ == '__main__':
    unittest.main()
