from pathlib import Path
import unittest
from lupa.lua53 import LuaRuntime

ROOT = Path(__file__).resolve().parents[1]


class TickWorkTests(unittest.TestCase):
    def setUp(self):
        self.lua = LuaRuntime(unpack_returned_tuples=True)
        for name in ('tests/lua/mock_world.lua', 'tests/lua/mock_trade.lua',
                     'mod/Baiqi/Lua/BaiqiConfig.lua', 'mod/Baiqi/Lua/BaiqiPolicy.lua',
                     'mod/Baiqi/Lua/BaiqiPlanner.lua'):
            self.lua.execute((ROOT / name).read_text(encoding='utf-8'))
        self.private = self.lua.execute(
            (ROOT / 'mod/Baiqi/Lua/BaiqiController.lua').read_text(encoding='utf-8')
            + '\nreturn {Pending=function() return pendingUnits end}\n')
        self.w = self.lua.globals().TestWorld
        self.c = self.lua.globals().BaiqiController
        self.lua.execute("TestWorld.queues[66]={{ProjectType='PROJECT_TEST'}};TestWorld.queues[67]={{ProjectType='PROJECT_TEST'}}")

    def observed_trade(self):
        self.c.RunNow()
        self.assertEqual((len(self.w.unitRequests), self.w.unitRequests[1].unit,
                          self.w.unitRequests[1].op), (1, 4, 18))
        self.assertIsNotNone(self.private.Pending()[4])
        self.lua.execute('TestWorld.routes={{TraderUnitID=4,DestinationCityPlayer=7,DestinationCityID=67}}')
        self.w.activeRoutes, self.w.activity = 1, 200

    def test_false_allow_orders_reconciles_without_new_orders(self):
        for busy in (False, True):
            with self.subTest(busy=busy):
                self.setUp()
                self.observed_trade()
                self.w.busy = busy
                self.c.RunNow(False)
                self.assertIsNone(self.private.Pending()[4])
                self.assertEqual(len(self.w.unitRequests), 1)

    def test_active_busy_tick_defers_receipts_then_idle_reconciles_without_replay(self):
        self.observed_trade()
        self.w.busy = True
        self.c.RunNow()
        self.assertIsNotNone(self.private.Pending()[4])
        self.assertEqual(len(self.w.unitRequests), 1)
        self.w.busy = False
        self.c.RunNow(False)
        self.assertIsNone(self.private.Pending()[4])
        self.assertEqual(len(self.w.unitRequests), 1)

    def test_known_manual_types_skip_position_reads_and_civilian_still_acts(self):
        for name in ('UNIT_WARRIOR', 'UNIT_SCOUT', 'UNIT_BATTERING_RAM',
                     'UNIT_GREAT_GENERAL', 'UNIT_GREAT_ADMIRAL',
                     'UNIT_APOSTLE', 'UNIT_INQUISITOR', 'UNIT_GURU'):
            with self.subTest(unit_type=name):
                self.setUp()
                self.lua.globals().ManualTestType = name
                self.lua.execute('''
GameInfo.Units[0].UnitType=ManualTestType
local w=TestWorld;w.manualPositionReads=0
local unit=w.objects.army;local x,y=unit.GetX,unit.GetY
unit.GetX=function(self) w.manualPositionReads=w.manualPositionReads+1;return x(self) end
unit.GetY=function(self) w.manualPositionReads=w.manualPositionReads+1;return y(self) end
''')
                self.c.RunNow()
                self.assertEqual(self.w.manualPositionReads, 0)
                self.assertEqual((len(self.w.unitRequests), self.w.unitRequests[1].unit,
                                  self.w.unitRequests[1].op), (1, 4, 18))
