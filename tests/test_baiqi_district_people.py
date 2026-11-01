"""Engineer and merchant consumers share native district activation without army access."""
from pathlib import Path
import unittest
from lupa.lua53 import LuaRuntime

ROOT = Path(__file__).resolve().parents[1]


class DistrictPeopleTests(unittest.TestCase):
    def setUp(self):
        self.lua = LuaRuntime(unpack_returned_tuples=True)
        for name in ('tests/lua/mock_world.lua', 'tests/lua/mock_scientist.lua'):
            self.lua.execute((ROOT/name).read_text(encoding='utf-8'))
        self.lua.execute('''
local w=TestWorld
local function row(table,name,index,hash,data)
 data.Index=index;data.Hash=hash;table[name]=data;table[index]=data;table[hash]=data
end
row(GameInfo.Units,'UNIT_GREAT_ENGINEER',6,206,{UnitType='UNIT_GREAT_ENGINEER'})
row(GameInfo.Units,'UNIT_GREAT_MERCHANT',7,207,{UnitType='UNIT_GREAT_MERCHANT'})
row(GameInfo.GreatPersonClasses,'GREAT_PERSON_CLASS_ENGINEER',6,906,{GreatPersonClassType='GREAT_PERSON_CLASS_ENGINEER'})
row(GameInfo.GreatPersonClasses,'GREAT_PERSON_CLASS_MERCHANT',7,907,{GreatPersonClassType='GREAT_PERSON_CLASS_MERCHANT'})
row(GameInfo.Districts,'DISTRICT_CITY_CENTER',0,700,{DistrictType='DISTRICT_CITY_CENTER'})
row(GameInfo.Districts,'DISTRICT_COMMERCIAL_HUB',8,708,{DistrictType='DISTRICT_COMMERCIAL_HUB'})
row(GameInfo.GreatPersonIndividuals,'GREAT_PERSON_INDIVIDUAL_BI_SHENG',71,771,
 {GreatPersonClassType='GREAT_PERSON_CLASS_ENGINEER',ActionRequiresCompletedDistrictType='DISTRICT_CITY_CENTER'})
row(GameInfo.GreatPersonIndividuals,'GREAT_PERSON_INDIVIDUAL_ZHANG_QIAN',72,772,
 {GreatPersonClassType='GREAT_PERSON_CLASS_MERCHANT',ActionRequiresCompletedDistrictType='DISTRICT_COMMERCIAL_HUB'})
function TestWorld.SetKind(kind)
 w.scientistType=kind;w.scientistClass=kind;w.scientistIndividual=kind==6 and 71 or 72
 w.requiredDistrict=kind==6 and 0 or 8
end
function w.objects.city:GetDistricts()
 return {HasDistrict=function(_,index,complete) assert(index==w.requiredDistrict and complete==true);return w.completed end,
  Members=function() local done=false;return function()
   if done then return end;done=true
   return 1,{GetType=function() return w.requiredDistrict end,GetX=function() return 3 end,GetY=function() return 3 end}
  end end}
end
''')
        for name in ('BaiqiConfig', 'BaiqiPolicy', 'BaiqiPlanner', 'BaiqiController'):
            self.lua.execute((ROOT/f'mod/Baiqi/Lua/{name}.lua').read_text(encoding='utf-8'))
        self.w = self.lua.globals().TestWorld
        self.c = self.lua.globals().BaiqiController
        self.logs = []
        self.lua.globals().print = lambda *args: self.logs.append(' '.join(map(str, args)))

    def test_engineer_center_and_merchant_hub_use_actual_target_then_exact_native_command(self):
        for kind in (6, 7):
            with self.subTest(kind=kind):
                self.setUp()
                self.w.SetKind(kind)
                self.c.RunNow()
                request = self.w.unitRequests[1]
                self.assertEqual((request.op, request.params[14], request.params[15]), (10, 3, 3))
                self.w.scientistPlot, self.w.scientistMoves = 43, 1
                self.c.Update(.35)
                self.assertEqual((len(self.w.commandRequests), self.w.commandRequests[1].hash), (1, 501))
                self.w.scientistCharges = 0
                self.c.RunNow()
                self.assertTrue(any('kind=ACTIVATE_GREAT_PERSON|charges=0' in line for line in self.logs))

    def test_consumed_engineer_or_merchant_accepts_only_exact_late_class_individual_event(self):
        for kind, individual in ((6, 71), (7, 72)):
            with self.subTest(kind=kind):
                self.setUp()
                self.w.SetKind(kind)
                self.w.scientistPlot = 43
                self.c.RunNow()
                self.w.withScientist = False
                self.c.Update(3600)
                for packet in ((7, 4, 5, individual), (7, 4, kind, 70), (8, 4, kind, individual)):
                    self.w.FireActivation(*packet)
                    self.c.RunNow()
                self.assertFalse(any('proof=native_activation_event' in line for line in self.logs))
                self.w.FireActivation(7, 4, 900+kind, 700+individual)
                self.c.RunNow()
                self.assertEqual(sum('proof=native_activation_event' in line for line in self.logs), 1)
                self.assertEqual(len(self.w.commandRequests), 1)

    def test_mismatched_unit_class_or_individual_never_moves_or_activates(self):
        for key, value in (('scientistClass', 7), ('scientistIndividual', 72)):
            with self.subTest(key=key):
                self.setUp()
                self.w.SetKind(6)
                self.w[key] = value
                self.c.RunNow()
                self.assertEqual((len(self.w.commandRequests), self.w.unitRequests[1].op), (0, 17))

    def test_suzerain_city_transfer_and_non_district_actions_are_not_automated(self):
        for change in ("ActionRequiresSuzerainTerritory=true", "ActionRequiresCompletedDistrictType=nil"):
            with self.subTest(change=change):
                self.setUp()
                self.w.SetKind(7)
                self.lua.execute('GameInfo.GreatPersonIndividuals[72].'+change)
                self.w.scientistPlot = 43
                self.c.RunNow()
                self.assertEqual((len(self.w.commandRequests), self.w.unitRequests[1].op), (0, 17))

    def test_military_great_people_and_other_classes_never_enter_policy_whitelist(self):
        policy = self.lua.globals().BaiqiPolicy
        for kind in ('UNIT_GREAT_GENERAL', 'UNIT_GREAT_ADMIRAL', 'UNIT_GREAT_PROPHET', 'UNIT_WARRIOR'):
            self.assertFalse(policy.CivilianType(kind))
            self.assertFalse(policy.ActionAllowed(kind, 'ACTIVATE_GREAT_PERSON'))
        for kind in ('UNIT_GREAT_WRITER', 'UNIT_GREAT_ARTIST', 'UNIT_GREAT_MUSICIAN'):
            self.assertIsNone(policy.DistrictGreatPersonClass(kind))

    def test_type_class_owner_or_individual_change_inside_native_gate_prevents_dispatch(self):
        for change in ('scientistType=7', 'scientistClass=7', 'scientistOwner=8', 'scientistIndividual=72', 'scientistID=99;TestWorld.scientistFormation=2'):
            with self.subTest(change=change):
                self.setUp()
                self.w.SetKind(6)
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

    def test_reused_native_unit_slot_or_wrong_class_cannot_confirm_consumption(self):
        for key, value in (('scientistID', 99), ('scientistClass', 7), ('scientistType', 7)):
            with self.subTest(key=key):
                self.setUp()
                self.w.SetKind(6)
                self.w.scientistPlot = 43
                self.c.RunNow()
                self.w[key] = value
                self.w.scientistCharges, self.w.findScientistAlias, self.w.scientistFormation = 0, True, 2
                self.c.Update(2)
                self.assertFalse(any('|kind=ACTIVATE_GREAT_PERSON|' in line for line in self.logs))
                self.assertTrue(any('awaiting_native_activation_event=true' in line for line in self.logs))


if __name__ == '__main__':
    unittest.main()
