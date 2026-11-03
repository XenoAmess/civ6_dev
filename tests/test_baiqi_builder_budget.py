from pathlib import Path
import math
import unittest
from lupa.lua53 import LuaRuntime

ROOT=Path(__file__).resolve().parents[1]


class BuilderClockTests(unittest.TestCase):
    def setUp(self):
        self.lua=LuaRuntime(unpack_returned_tuples=True)
        for name in ('tests/lua/mock_world.lua','mod/Baiqi/Lua/BaiqiConfig.lua',
                     'mod/Baiqi/Lua/BaiqiPolicy.lua','mod/Baiqi/Lua/BaiqiPlanner.lua'):
            self.lua.execute((ROOT/name).read_text(encoding='utf-8'))
        self.private=self.lua.execute((ROOT/'mod/Baiqi/Lua/BaiqiController.lua').read_text(encoding='utf-8')
                                     +'\nreturn {Clock=PlanningTime,Expired=BuilderBudgetExpired}')

    def test_zero_boundary_single_read_and_changing_clock(self):
        self.lua.execute('TestClock=0;TestClockCalls=0;Automation={GetTime=function() TestClockCalls=TestClockCalls+1;return TestClock end}')
        self.assertEqual(self.private.Clock(),0)
        self.lua.globals().TestClock=.5
        self.assertIs(self.private.Expired(.25,.25),True)
        self.lua.globals().TestClock=.375
        self.assertIs(self.private.Expired(.25,.25),False)
        self.lua.globals().TestClock=.75
        self.assertIs(self.private.Expired(.25,.25),True)
        self.assertEqual(self.lua.globals().TestClockCalls,4)

    def test_missing_invalid_throwing_and_backward_clocks_fall_back(self):
        variants=('Automation=nil','Automation={}','Automation={GetTime=3}',
                  'Automation={GetTime=function() error("clock failure") end}',
                  'Automation={GetTime=function() return nil end}',
                  'Automation={GetTime=function() return "x" end}',
                  'Automation={GetTime=function() return 0/0 end}',
                  'Automation={GetTime=function() return math.huge end}',
                  'Automation={GetTime=function() return -math.huge end}',
                  'Automation={GetTime=function() return -1 end}')
        for code in variants:
            with self.subTest(code=code):
                self.lua.execute(code)
                self.assertIsNone(self.private.Clock())
                self.assertIs(self.private.Expired(0,.125),False)
        self.lua.execute('Automation={GetTime=function() return .125 end}')
        self.assertIs(self.private.Expired(.25,.125),False)

    def test_invalid_arguments_return_false_without_reading_clock(self):
        self.lua.execute('TestClockCalls=0;Automation={GetTime=function() TestClockCalls=TestClockCalls+1;return 1 end}')
        for value in (None,False,True,'x',-1,math.nan,math.inf,-math.inf):
            with self.subTest(started=value):
                self.assertIs(self.private.Expired(value,.125),False)
        for value in (None,False,True,'x',0,-1,math.nan,math.inf,-math.inf):
            with self.subTest(limit=value):
                self.assertIs(self.private.Expired(0,value),False)
        self.assertEqual(self.lua.globals().TestClockCalls,0)
