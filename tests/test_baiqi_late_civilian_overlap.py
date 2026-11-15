"""Reconsider an unchanged civilian after a visible overlap arrives later."""
import unittest
from lupa.lua51 import LuaRuntime as Lua51
from lupa.lua53 import LuaRuntime as Lua53
import test_baiqi_civilian_overlap as overlap_fixture


class LateCivilianOverlapTests(unittest.TestCase):
    runtime = Lua53

    def setUp(self):
        overlap_fixture.CivilianOverlapTests.setUp(self)
        self.lua.execute('''
local w=TestWorld;local player=w.objects.player
local collection=player:GetUnits();local scientist=collection:FindID(4);local general=collection:FindID(5)
w.lateScientist=scientist;w.lateGeneral=general;w.generalAtOrigin=false;w.allowWait=false
GameInfo.Units[4].FormationClass='FORMATION_CLASS_CIVILIAN'
general.GetX=function()return w.generalAtOrigin and 2 or 3 end
general.GetY=function()return 3 end
scientist.IsReadyToSelect=function()return true end
scientist.IsDead=function()return w.nativeDead==true end
scientist.IsDelayedDeath=function()return w.nativeDelayed==true end
scientist.HasPendingOperations=function()if w.nativePendingUnknown then return nil end;return w.nativePending==true end
ActivityTypes=ActivityTypes or {};ActivityTypes.ACTIVITY_AWAKE=1797587246
UnitManager.GetActivityType=function()return ActivityTypes.ACTIVITY_AWAKE end
GameInfo.UnitOperations=GameInfo.UnitOperations or {}
GameInfo.UnitOperations.UNITOPERATION_SKIP_TURN={Hash=UnitOperationTypes.SKIP_TURN}
UnitManager.GetQueuedDestination=function()return w.queuedDestination end
local hostile=setmetatable({GetOwner=function()return 8 end,GetID=function()return 99 end},{__index=general})
Units.GetUnitsInPlot=function(plot)
 if plot:GetIndex()==42 then
  local group={scientist};if w.generalAtOrigin then group[#group+1]=general end
  if w.originThreat then group[#group+1]=hostile end
  return group
 elseif plot:GetIndex()==43 and not w.generalAtOrigin then return{general}end
 return{}
end
''')

    def prime(self):
        self.c.RunNow()
        self.assertEqual(len(self.w.unitRequests), 0)
        self.w.generalAtOrigin = True

    def test_late_occupant_moves_only_the_previously_evaluated_civilian(self):
        self.prime()
        before = (self.w.lateScientist.GetID(), self.w.scientistPlot, self.w.scientistMoves)
        self.c.RunNow()
        self.assertEqual([(r.unit, r.op) for r in self.w.unitRequests.values()], [(4, 10)])
        self.assertEqual((self.w.unitRequests[1].params[14], self.w.unitRequests[1].params[15]), (3, 3))
        self.assertEqual(before, (4, self.w.scientistPlot, self.w.scientistMoves))
        self.c.RunNow()
        self.assertEqual(len(self.w.unitRequests), 1)

    def test_same_overlap_can_be_reconsidered_after_visible_threat_is_gone(self):
        self.w.generalAtOrigin, self.w.originThreat = True, True
        self.c.RunNow()
        self.assertEqual(len(self.w.unitRequests), 0)
        self.w.originThreat = False
        self.c.RunNow()
        self.assertEqual([(r.unit, r.op) for r in self.w.unitRequests.values()], [(4, 10)])

    def test_actual_arrival_permits_normal_wait_without_duplicate_move(self):
        self.prime(); self.c.RunNow()
        self.assertEqual(len(self.w.unitRequests), 1)
        self.c.RunNow(); self.assertEqual(len(self.w.unitRequests), 1)
        self.w.scientistPlot, self.w.allowWait = 43, True
        self.c.Update(.5)
        self.assertEqual([r.op for r in self.w.unitRequests.values()], [10, 17])

    def test_held_or_unknown_ability_never_moves_the_evaluated_actor(self):
        for result in ("return 'ARMED'", "return 'LEGACY_UNKNOWN'", "return 'UNAVAILABLE'",
                       'return nil', "error('unavailable')"):
            with self.subTest(result=result):
                self.setUp(); self.prime()
                self.lua.execute('ExposedMembers.BaiqiGreatPersonIntentBridge.Inspect=function() '+result+' end')
                self.c.RunNow()
                self.assertEqual(len(self.w.unitRequests), 0)

    def test_native_pending_or_unknown_queue_never_gets_replaced(self):
        for change in ('TestWorld.nativePending=true', 'TestWorld.nativePendingUnknown=true',
                       'TestWorld.queuedDestination=43',
                       'UnitManager.GetQueuedDestination=function()return nil,nil end',
                       'UnitManager.GetQueuedDestination=nil',
                       'TestWorld.lateScientist.HasPendingOperations=nil'):
            with self.subTest(change=change):
                self.setUp(); self.prime(); self.lua.execute(change)
                self.c.RunNow()
                self.assertEqual(len(self.w.unitRequests), 0)

    def test_escort_military_or_context_loss_never_gets_relocation(self):
        for change in ('TestWorld.scientistFormation=2', 'TestWorld.scientistType=4',
                       'TestWorld.strategic=false', 'TestWorld.busy=true',
                       'TestWorld.nativeDead=true', 'TestWorld.nativeDelayed=true'):
            with self.subTest(change=change):
                self.setUp(); self.prime(); self.lua.execute(change)
                self.c.RunNow()
                self.assertEqual(len(self.w.unitRequests), 0)

    def test_fresh_move_qualification_cannot_change_held_pending_or_formation(self):
        for change in ("ExposedMembers.BaiqiGreatPersonIntentBridge.Inspect=function()return 'ARMED'end",
                       'TestWorld.nativePending=true', 'TestWorld.queuedDestination=43',
                       'TestWorld.scientistFormation=2', 'TestWorld.generalAtOrigin=false'):
            with self.subTest(change=change):
                self.setUp(); self.prime()
                self.lua.execute('''local old=UnitManager.CanStartOperation
UnitManager.CanStartOperation=function(u,op,...)
 local result=old(u,op,...)
 if op==UnitOperationTypes.MOVE_TO then '''+change+''' end
 return result
end''')
                self.c.RunNow()
                self.assertEqual(len(self.w.unitRequests), 0)

    def test_no_overlap_never_starts_roaming(self):
        self.c.RunNow(); self.c.RunNow(); self.c.Update(3)
        self.assertEqual(len(self.w.unitRequests), 0)


class LateCivilianOverlapLua51Tests(LateCivilianOverlapTests):
    runtime = Lua51


if __name__ == '__main__':
    unittest.main()
