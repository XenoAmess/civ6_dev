from pathlib import Path
import unittest
from lupa.lua53 import LuaRuntime

ROOT = Path(__file__).resolve().parents[1]


class CityEarlyTests(unittest.TestCase):
    def setUp(self):
        self.lua = LuaRuntime(unpack_returned_tuples=True)
        for name in ('tests/lua/mock_world.lua', 'tests/lua/mock_trade.lua',
                     'tests/lua/mock_military.lua', 'tests/lua/mock_standby.lua',
                     'mod/Baiqi/Lua/BaiqiConfig.lua', 'mod/Baiqi/Lua/BaiqiPolicy.lua',
                     'mod/Baiqi/Lua/BaiqiPlanner.lua'):
            self.lua.execute((ROOT / name).read_text(encoding='utf-8'))
        self.private = self.lua.execute(
            (ROOT / 'mod/Baiqi/Lua/BaiqiController.lua').read_text(encoding='utf-8') + '''
return {Evaluated=function() return cityEvaluated end,
 RunCity=function(city) local ctx,player,state=PlayerContext();return ProcessCity(ctx,player,state,city) end}
''')
        self.w = self.lua.globals().TestWorld
        self.c = self.lua.globals().BaiqiController
        self.lua.execute('''
local w=TestWorld;w.cityQueueReads=0;w.rejectStandby=true
local original=w.objects.city.GetBuildQueue
w.objects.city.GetBuildQueue=function(self)
 w.cityQueueReads=w.cityQueueReads+1
 return original(self)
end
''')
        self.c.RunNow(False)

    def test_same_turn_evaluated_city_skips_actual_queue_getter(self):
        self.private.Evaluated()[66] = self.w.turn
        self.assertFalse(self.private.RunCity(self.w.objects.city))
        self.assertEqual(self.w.cityQueueReads, 0)
        self.assertEqual(len(self.w.cityRequests), 0)

    def test_refresh_and_new_turn_restore_fresh_queue_evaluation(self):
        self.private.Evaluated()[66] = self.w.turn
        self.private.RunCity(self.w.objects.city)
        self.assertEqual(self.w.cityQueueReads, 0)
        self.c.RefreshProduction()
        self.private.RunCity(self.w.objects.city)
        self.assertGreater(self.w.cityQueueReads, 0)
        self.assertEqual(self.private.Evaluated()[66], self.w.turn)
        before = self.w.cityQueueReads
        self.private.RunCity(self.w.objects.city)
        self.assertEqual(self.w.cityQueueReads, before)
        self.w.turn += 1
        self.c.RunNow(False)
        self.assertIsNone(self.private.Evaluated()[66])
        self.private.RunCity(self.w.objects.city)
        self.assertGreater(self.w.cityQueueReads, before)
        self.assertEqual(self.private.Evaluated()[66], self.w.turn)
        self.assertEqual(len(self.w.cityRequests), 0)
