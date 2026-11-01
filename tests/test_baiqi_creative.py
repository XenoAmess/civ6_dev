"""Zero-charge creators require an exact native event and a real newly owned work."""
from pathlib import Path
import unittest
from lupa.lua53 import LuaRuntime

ROOT = Path(__file__).resolve().parents[1]


class CreativeTests(unittest.TestCase):
    def setUp(self):
        self.lua = LuaRuntime(unpack_returned_tuples=True)
        for name in ('tests/lua/mock_world.lua', 'tests/lua/mock_scientist.lua', 'tests/lua/mock_creative.lua'):
            self.lua.execute((ROOT/name).read_text(encoding='utf-8'))
        for name in ('BaiqiConfig', 'BaiqiPolicy', 'BaiqiPlanner', 'BaiqiController'):
            self.lua.execute((ROOT/f'mod/Baiqi/Lua/{name}.lua').read_text(encoding='utf-8'))
        self.w = self.lua.globals().TestWorld
        self.c = self.lua.globals().BaiqiController
        self.logs = []
        self.lua.globals().print = lambda *args: self.logs.append(' '.join(map(str, args)))

    def observed(self):
        return [line for line in self.logs if '|kind=CREATE_GREAT_WORK|' in line]

    def test_all_three_zero_charge_creator_classes_move_to_actual_compatible_building_and_create(self):
        for kind in (6, 7, 8):
            with self.subTest(kind=kind):
                self.setUp()
                self.w.SetCreativeKind(kind)
                self.c.RunNow()
                self.assertEqual((self.w.unitRequests[1].op, self.w.unitRequests[1].params[14]), (10, 3))
                self.w.scientistPlot, self.w.scientistMoves = 43, 1
                self.c.Update(.35)
                self.assertEqual((len(self.w.commandRequests), self.w.commandRequests[1].hash), (1, 501))
                self.w.PlaceWork(91, 0)
                self.w.FireWork(7, 4, 2, 3, 2, 91)
                self.c.RunNow()
                self.assertEqual(len(self.observed()), 1)

    def test_work_without_exact_unit_event_or_event_without_real_slot_cannot_confirm(self):
        self.w.scientistPlot = 43
        self.c.RunNow()
        self.w.PlaceWork(91, 0)
        self.c.RunNow()
        for packet in ((7, 80, 2, 3, 2, 91), (8, 4, 2, 3, 2, 91), (7, 99, 2, 3, 2, 91)):
            self.w.FireWork(*packet)
            self.c.RunNow()
        self.assertFalse(self.observed())
        self.w.FireWork(7, 4, 2, 3, 2, 92)
        self.c.Update(10)
        self.assertFalse(self.observed())
        self.w.FireWork(7, 4, 2, 3, 2, 91)
        self.c.RunNow()
        self.assertEqual(len(self.observed()), 1)

    def test_event_before_slot_update_and_consumed_unit_wait_across_turns_without_repeat(self):
        self.w.scientistPlot = 43
        self.c.RunNow()
        self.w.FireWork(7, 4, 2, 3, 2, 91)
        self.w.withScientist = False
        self.w.turn += 1
        self.c.Update(3600)
        self.assertFalse(self.observed())
        self.assertEqual(sum('great_work_request_unresolved' in line for line in self.logs), 1)
        self.w.PlaceWork(91, 0)
        self.c.RunNow()
        self.w.FireWork(7, 4, 2, 3, 2, 91)
        self.c.RunNow()
        self.assertEqual((len(self.observed()), len(self.w.commandRequests)), (1, 1))

    def test_old_work_other_individual_foreign_city_and_wrong_city_cannot_prove_creation(self):
        for mode in ('old', 'other', 'foreign', 'wrong_city'):
            with self.subTest(mode=mode):
                self.setUp()
                if mode == 'old':
                    self.lua.execute('TestWorld.slots={91,-1};TestWorld.workTypes[91]=0')
                self.w.scientistPlot = 43
                self.c.RunNow()
                self.w.PlaceWork(91, 2 if mode == 'other' else 0)
                if mode == 'foreign':
                    self.w.cityOwner = 8
                self.w.FireWork(7, 4, 9 if mode == 'wrong_city' else 2, 3, 2, 91)
                self.c.Update(10)
                self.assertFalse(self.observed())
                self.assertEqual(len(self.w.commandRequests), 1)

    def test_full_incompatible_pillaged_or_hidden_building_never_gets_background_activation(self):
        for mode in ('full', 'incompatible', 'pillaged', 'hidden'):
            with self.subTest(mode=mode):
                self.setUp()
                if mode == 'full':
                    self.w.PlaceWork(91, 0)
                elif mode == 'incompatible':
                    self.w.slotType = 1
                elif mode == 'pillaged':
                    self.w.buildingPillaged = True
                else:
                    self.w.hiddenTarget = True
                self.c.RunNow()
                self.assertEqual((len(self.w.commandRequests), self.w.unitRequests[1].op), (0, 17))

    def test_wrong_class_and_final_owner_or_position_change_prevent_creation(self):
        self.w.scientistClass = 7
        self.c.RunNow()
        self.assertEqual(len(self.w.commandRequests), 0)
        for change in ('scientistOwner=8', 'scientistPlot=42', 'scientistClass=7'):
            with self.subTest(change=change):
                self.setUp()
                self.w.scientistPlot = 43
                self.lua.execute('''
local original=UnitManager.CanStartCommand
UnitManager.CanStartCommand=function(...)
 local result=original(...);TestWorld.'''+change+''';return result
end
''')
                self.c.RunNow()
                self.assertEqual(len(self.w.commandRequests), 0)
                self.assertFalse(any('BAIQI|error' in line for line in self.logs), self.logs)

    def test_creator_unknown_keeps_single_request_and_shutdown_removes_event(self):
        self.w.scientistPlot = 43
        self.c.RunNow()
        self.w.turn += 1
        self.c.Update(3600)
        self.c.Update(3600)
        self.assertEqual((len(self.w.commandRequests), len(self.w.unitRequests)), (1, 0))
        self.assertEqual(sum('great_work_request_unresolved' in line for line in self.logs), 1)
        self.assertEqual(self.w.WorkSubscriptions(), 1)
        self.c.Shutdown()
        self.assertEqual(self.w.WorkSubscriptions(), 0)

    def test_two_creators_cannot_request_the_last_empty_slot_while_first_is_unconfirmed(self):
        self.w.scientistPlot = 43
        self.lua.execute('''
local player=TestWorld.objects.player;local original=player.GetUnits
local secondary
player.GetUnits=function(self)
 local units=original(self);local list={}
 for _,unit in units:Members() do list[#list+1]=unit end
 if not secondary then
  local first=list[#list];secondary=setmetatable({GetID=function() return 55 end},{__index=first})
 end
 list[#list+1]=secondary
 return {Members=function() local i=0;return function() i=i+1;if list[i] then return i,list[i] end end end,
  FindID=function(_,id) if id==55 then return secondary end;return units:FindID(id) end}
end
UnitManager.RequestOperation=function(unit,op,params)
 TestWorld.unitRequests[#TestWorld.unitRequests+1]={unit=unit:GetID(),op=op,params=params}
end
''')
        self.c.RunNow()
        self.c.Update(1)
        self.assertEqual(len(self.w.commandRequests), 1)
        self.assertEqual((self.w.unitRequests[1].unit, self.w.unitRequests[1].op), (55, 17))
        self.assertFalse(any('BAIQI|error' in line for line in self.logs), self.logs)


if __name__ == '__main__':
    unittest.main()
