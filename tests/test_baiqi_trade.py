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

    def test_pending_production_reserves_each_role_before_any_queue_ack(self):
        for unit_hash, extra_army in ((203, 0), (202, 0), (201, 0), (200, 2)):
            with self.subTest(unit_hash=unit_hash):
                self.setUp()
                self.w.withTrader, self.w.productionMode = False, True
                self.w.productionHash, self.w.extraArmy = unit_hash, extra_army
                if unit_hash == 201:
                    self.w.EnableSettlerSite()
                self.c.RunNow()
                self.c.RunNow()  # Native queue still empty: request is in flight.
                self.assertEqual(len(self.w.cityRequests), 1, self.c.GetStatus())
                self.assertEqual(self.w.cityRequests[1].params[4], unit_hash)

    def test_pending_then_native_index_queue_does_not_double_count_capacity(self):
        self.w.withTrader, self.w.productionMode, self.w.tradeCapacity = False, True, 2
        self.c.RunNow()
        # Native GetAt uses a unit index, not the candidate's scan ordinal.
        self.lua.execute('TestWorld.queues[66]={{UnitType=3}}')
        self.c.RunNow()
        self.assertEqual(len(self.w.cityRequests), 2)
        self.assertEqual(self.w.cityRequests[2].city, 67)
        self.c.RunNow()
        self.assertEqual(len(self.w.cityRequests), 2)

    def test_pending_and_queued_maintenance_each_reserve_budget_once(self):
        self.w.withTrader, self.w.productionMode, self.w.tradeCapacity = False, True, 3
        self.lua.execute('''
          GameInfo.Units.UNIT_TRADER.Maintenance=1
          TestWorld.objects.player.GetTreasury=function() return {
            GetGoldBalance=function() return 100 end,GetGoldYield=function() return 3 end,
            GetTotalMaintenance=function() return 0 end} end
        ''')
        self.c.RunNow()
        self.c.RunNow()
        self.assertEqual(len(self.w.cityRequests), 1)
        self.lua.execute('TestWorld.queues[66]={{UnitType=3}}')
        self.c.RunNow()
        self.assertEqual(len(self.w.cityRequests), 1)

    def test_rejected_production_chooses_different_legal_item_same_turn_without_replay(self):
        self.w.withTrader, self.w.productionMode = False, True
        self.w.allowProject, self.w.blockSecondCity = True, True
        self.c.RunNow()
        self.c.Update(1)
        self.assertEqual(len(self.w.cityRequests), 1)
        self.w.busy = True
        self.c.Update(2)
        self.assertEqual(len(self.w.cityRequests), 1)
        self.w.busy, self.w.processing = False, True
        self.c.Update(2)
        self.assertEqual(len(self.w.cityRequests), 1)
        self.w.processing = False
        self.c.Update(0.35)
        self.assertEqual(len(self.w.cityRequests), 2)
        self.assertEqual((self.w.cityRequests[2].city, self.w.cityRequests[2].params[5]), (66, 301))
        self.c.Update(3)
        self.assertEqual(len(self.w.cityRequests), 2)

    def test_delayed_accepted_queue_waits_and_unrelated_queue_is_not_confirmation(self):
        self.w.withTrader, self.w.productionMode = False, True
        self.w.blockSecondCity, self.w.allowProject = True, True
        logs = []
        self.lua.globals().print = lambda *args: logs.append(' '.join(map(str, args)))
        self.c.RunNow()
        self.c.Update(1.5)
        self.assertEqual(len(self.w.cityRequests), 1)
        self.lua.execute('TestWorld.queues[66]={{ProjectType="PROJECT_TEST"}}')
        self.c.Update(0.35)
        self.assertEqual(len(self.w.cityRequests), 1)
        self.assertTrue(any('queue_request_superseded' in line for line in logs), logs)
        self.assertFalse(any('queue_observed' in line for line in logs), logs)

    def test_pending_city_ownership_loss_cannot_trigger_another_write(self):
        self.w.withTrader, self.w.productionMode, self.w.blockSecondCity = False, True, True
        logs = []
        self.lua.globals().print = lambda *args: logs.append(' '.join(map(str, args)))
        self.c.RunNow()
        self.lua.execute('TestWorld.objects.city.GetOwner=function() return 8 end')
        self.c.Update(3)
        self.w.turn += 1
        self.c.RunNow()
        self.assertEqual(len(self.w.cityRequests), 1)
        self.assertTrue(any('reason=city_unavailable' in line for line in logs), logs)


if __name__ == '__main__':
    unittest.main()
