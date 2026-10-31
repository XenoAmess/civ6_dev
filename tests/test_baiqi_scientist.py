"""Nonmilitary scientific activation uses exact native command and charge readback."""
from pathlib import Path
import unittest
from lupa.lua53 import LuaRuntime

ROOT = Path(__file__).resolve().parents[1]


class BaiqiScientistTests(unittest.TestCase):
    def setUp(self):
        self.lua = LuaRuntime(unpack_returned_tuples=True)
        for path in ('tests/lua/mock_world.lua', 'tests/lua/mock_scientist.lua',
                     'mod/Baiqi/Lua/BaiqiConfig.lua', 'mod/Baiqi/Lua/BaiqiPolicy.lua',
                     'mod/Baiqi/Lua/BaiqiPlanner.lua', 'mod/Baiqi/Lua/BaiqiController.lua'):
            self.lua.execute((ROOT/path).read_text(encoding='utf-8'))
        self.w = self.lua.globals().TestWorld
        self.c = self.lua.globals().BaiqiController
        self.logs = []
        self.lua.globals().print = lambda *args: self.logs.append(' '.join(map(str, args)))

    def test_scientist_moves_to_real_district_coordinates_then_uses_exact_native_command(self):
        self.c.RunNow()
        request = self.w.unitRequests[1]
        self.assertEqual((request.unit,request.op,request.params[14],request.params[15]), (4,10,3,3))
        self.w.queuedDestination = 43
        self.c.Update(2)
        self.assertEqual(len(self.w.commandRequests), 0)
        self.w.queuedDestination, self.w.scientistPlot, self.w.scientistMoves = None, 43, 1
        self.c.RunNow()
        self.assertEqual((len(self.w.commandRequests),self.w.commandRequests[1].hash), (1,501))
        self.w.scientistReady, self.w.scientistMoves = False, 0
        self.c.Update(2)
        self.assertFalse(any('kind=ACTIVATE_GREAT_PERSON|charges=' in l for l in self.logs))
        self.w.scientistCharges = 0
        self.c.RunNow()
        self.assertTrue(any('kind=ACTIVATE_GREAT_PERSON|charges=0' in l for l in self.logs), self.logs)
        self.assertEqual(len(self.w.commandRequests), 1)

    def test_position_or_moves_do_not_confirm_activation_and_busy_delay_does_not_repeat(self):
        self.w.scientistPlot = 43
        self.c.RunNow()
        self.w.busy, self.w.scientistReady = True, False
        self.w.scientistPlot, self.w.scientistMoves = 42, 1
        self.c.Update(3)
        self.assertEqual(len(self.w.commandRequests), 1)
        self.assertEqual(len(self.w.unitRequests), 0)
        self.assertFalse(any('kind=ACTIVATE_GREAT_PERSON|charges=' in l for l in self.logs))
        self.w.scientistCharges, self.w.scientistMoves = 0, 0
        self.c.RunNow()
        self.assertTrue(any('kind=ACTIVATE_GREAT_PERSON|charges=0' in l for l in self.logs), self.logs)

    def test_unaccepted_activation_waits_and_never_repeats_same_charge_in_turn(self):
        self.w.scientistPlot = 43
        self.c.RunNow()
        self.c.Update(0.35)
        self.assertEqual(len(self.w.commandRequests), 1)
        self.c.Update(0.35)
        self.assertEqual((len(self.w.commandRequests),len(self.w.unitRequests),self.w.unitRequests[1].op), (1,1,17))
        self.c.Update(2)
        self.assertEqual(len(self.w.commandRequests), 1)
        self.w.turn += 1
        self.c.RunNow()
        self.assertEqual(len(self.w.commandRequests), 2)

    def test_escort_foreign_owner_and_other_leader_never_receive_background_actions(self):
        self.w.scientistFormation = 2
        self.c.RunNow()
        self.assertEqual((len(self.w.commandRequests),len(self.w.unitRequests)), (0,0))
        self.w.scientistFormation, self.w.scientistOwner = 1, 8
        self.w.turn += 1
        self.c.RunNow()
        self.assertEqual((len(self.w.commandRequests),len(self.w.unitRequests)), (0,0))
        self.w.scientistOwner = 7
        self.lua.execute("PlayerConfigurations[7].GetLeaderTypeName=function() return 'LEADER_TRAJAN' end")
        self.c.RunNow()
        self.assertEqual((len(self.w.commandRequests),len(self.w.unitRequests)), (0,0))

    def test_unsupported_scientist_conditions_wait_without_invented_activation(self):
        self.lua.execute('GameInfo.GreatPersonIndividuals[70].ActionRequiresCompletedDistrictType=nil')
        self.c.RunNow()
        self.assertEqual((len(self.w.commandRequests),self.w.unitRequests[1].op), (0,17))

    def test_incomplete_hidden_or_visible_threat_district_is_not_a_move_target(self):
        for key,value in (('completed',False), ('hiddenTarget',True), ('enemy',True)):
            with self.subTest(key=key):
                self.setUp()
                self.w[key] = value
                self.c.RunNow()
                self.assertEqual((len(self.w.commandRequests),self.w.unitRequests[1].op), (0,17))
        self.setUp()
        self.w.enemy, self.w.hiddenEnemy = True, True
        self.c.RunNow()
        self.assertEqual((self.w.scientistUnitReads,self.w.unitRequests[1].op), (0,10))

    def test_owner_change_or_unit_removal_is_unavailable_not_activation_success(self):
        for removed in (False, True):
            with self.subTest(removed=removed):
                self.setUp()
                self.w.scientistPlot = 43
                self.c.RunNow()
                if removed:
                    self.w.withScientist = False
                else:
                    self.w.scientistOwner = 8
                self.c.Update(1)
                self.assertEqual(len(self.w.commandRequests), 1)
                self.assertTrue(any('great_person_request_unavailable' in l for l in self.logs), self.logs)
                self.assertFalse(any('kind=ACTIVATE_GREAT_PERSON|charges=' in l for l in self.logs))
                self.c.Update(10)
                self.assertEqual(sum('great_person_request_unavailable' in l for l in self.logs), 1)

    def test_consumed_unit_keeps_correlation_for_late_activation_event_without_timeout(self):
        self.w.scientistPlot = 43
        self.c.RunNow()
        self.w.withScientist = False
        self.c.Update(2)
        self.w.turn += 1
        self.c.Update(3600)
        for packet in ((8,4,5,70), (7,99,5,70), (7,4,0,70), (7,4,5,99)):
            self.w.FireActivation(*packet)
            self.c.RunNow()
        self.assertFalse(any('proof=native_activation_event' in l for l in self.logs))
        self.w.FireActivation(7,4,5,70)
        self.c.RunNow()
        self.w.FireActivation(7,4,5,70)
        self.c.RunNow()
        self.assertEqual(sum('proof=native_activation_event' in l for l in self.logs), 1)
        self.assertEqual(sum('great_person_request_unavailable' in l for l in self.logs), 1)
        self.assertEqual((len(self.w.commandRequests),len(self.w.unitRequests)), (1,0))

    def test_replacement_unit_or_individual_cannot_prove_old_activation_from_zero_charges(self):
        for replacement in ('id', 'type', 'individual'):
            with self.subTest(replacement=replacement):
                self.setUp()
                self.w.scientistPlot = 43
                self.c.RunNow()
                self.w.scientistCharges = 0
                if replacement == 'id':
                    self.w.scientistID, self.w.findScientistAlias, self.w.scientistFormation = 99, True, 2
                elif replacement == 'type':
                    self.w.scientistType = 0
                else:
                    self.lua.execute("GameInfo.GreatPersonIndividuals[71]={Index=71,GreatPersonClassType='GREAT_PERSON_CLASS_SCIENTIST'}")
                    self.w.scientistIndividual = 71
                self.c.Update(2)
                self.assertFalse(any('|kind=ACTIVATE_GREAT_PERSON|' in l for l in self.logs))
                self.assertTrue(any('awaiting_native_activation_event=true' in l for l in self.logs))
                self.w.withScientist, self.w.findScientistAlias = False, False
                self.w.FireActivation(7,4,5,70)
                self.c.RunNow()
                self.assertEqual(sum('proof=native_activation_event' in l for l in self.logs), 1)
                self.assertEqual((len(self.w.commandRequests),len(self.w.unitRequests)), (1,0))

    def test_matching_native_activation_event_confirms_consumed_unit_and_unrelated_events_do_not(self):
        self.w.scientistPlot = 43
        self.c.RunNow()
        for packet in ((8,4,5,70), (7,99,5,70), (7,4,0,70), (7,4,5,99)):
            self.w.FireActivation(*packet)
            self.c.RunNow()
        self.assertFalse(any('proof=native_activation_event' in l for l in self.logs))
        self.w.withScientist = False
        self.w.FireActivation(7,4,5,70)
        self.c.RunNow()
        self.assertTrue(any('proof=native_activation_event' in l for l in self.logs), self.logs)
        self.assertEqual(len(self.w.commandRequests), 1)

    def test_shutdown_removes_scientist_event_subscription(self):
        self.assertEqual(self.w.ActivationSubscriptions(), 1)
        self.c.Shutdown()
        self.assertEqual(self.w.ActivationSubscriptions(), 0)

    def test_activation_event_identity_is_normalized_through_real_data_rows(self):
        self.w.scientistPlot = 43
        self.c.RunNow()
        self.w.withScientist = False
        self.w.FireActivation(7,4,905,770)
        self.c.RunNow()
        self.assertTrue(any('proof=native_activation_event' in l for l in self.logs), self.logs)

    def test_scientist_arrives_and_activates_using_xy_with_stale_plot_id(self):
        self.w.stalePlotId = 99
        self.c.RunNow()
        self.assertEqual(self.w.unitRequests[1].op, 10)
        self.w.scientistPlot, self.w.stalePlotId = 43, 42
        self.c.Update(0.35)
        self.assertEqual(len(self.w.commandRequests), 1)

    def test_activation_cannot_cross_a_position_change_during_legality_check(self):
        self.w.scientistPlot = 43
        self.lua.execute('''
local original=UnitManager.CanStartCommand
UnitManager.CanStartCommand=function(...)
 local result=original(...);TestWorld.scientistPlot=42;return result
end
''')
        self.c.RunNow()
        self.assertEqual(len(self.w.commandRequests), 0)


if __name__ == '__main__':
    unittest.main()
