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

    def target_threat_geometry(self, occupied_alternative=False):
        self.w.occupiedSafeAlternative = occupied_alternative
        self.lua.execute('''
local w=TestWorld
local origin,target=Map.GetPlotByIndex(42),Map.GetPlotByIndex(43)
local function Cell(index,x,y)
 return {GetIndex=function()return index end,GetX=function()return x end,
  GetY=function()return y end,GetOwner=function()return 7 end,
  IsWater=function()return false end,IsImpassable=function()return false end}
end
local cells={[42]=origin,[43]=target,[45]=Cell(45,5,3),[46]=Cell(46,2,4)}
Map.GetPlotByIndex=function(index)return cells[index]end
Map.GetPlot=function(x,y)
 for _,p in pairs(cells)do if p:GetX()==x and p:GetY()==y then return p end end
end
Map.GetPlotDistance=function(x,y,xx,yy)return math.abs(x-xx)+math.abs(y-yy)end
Map.GetPlotXYWithRangeCheck=function(x,y,dx,dy,r)
 if math.abs(dx)+math.abs(dy)<=r then return Map.GetPlot(x+dx,y+dy)end
end
Map.GetAdjacentPlot=function(x,y,d)
 if x==2 and y==3 then
  if d==0 then return target end
  if d==1 and w.occupiedSafeAlternative then return cells[46]end
 end
end
local hostile=setmetatable({GetOwner=function()return 8 end,GetID=function()return 99 end},{__index=w.lateGeneral})
local occupant=setmetatable({GetID=function()return 55 end,GetX=function()return 2 end,
 GetY=function()return 4 end},{__index=w.lateScientist})
local previous=Units.GetUnitsInPlot
Units.GetUnitsInPlot=function(p)
 if p:GetIndex()==45 then return w.targetThreat and {hostile}or{}end
 if p:GetIndex()==46 then return w.occupiedSafeAlternative and {occupant}or{}end
 return previous(p)
end
w.targetThreat=true
assert(Map.GetPlotDistance(2,3,5,3)>BaiqiConfig.threatRadius)
assert(Map.GetPlotDistance(3,3,5,3)<=BaiqiConfig.threatRadius)
assert(#Units.GetUnitsInPlot(cells[45])==1)
''')

    def check_target_threat_then_removal(self):
        self.prime()
        before = (self.w.lateScientist.GetID(), self.w.scientistPlot, self.w.scientistMoves)
        self.assertEqual(len(self.lua.globals().Units.GetUnitsInPlot(
            self.lua.globals().Map.GetPlotByIndex(43))), 0)
        self.c.RunNow(); self.c.Update(3)
        self.assertEqual(len(self.w.unitRequests), 0)
        self.assertEqual(before, (4, self.w.scientistPlot, self.w.scientistMoves))
        self.w.targetThreat = False
        self.c.RunNow()
        self.assertEqual([(r.unit, r.op) for r in self.w.unitRequests.values()], [(4, 10)])
        self.assertEqual((self.w.unitRequests[1].params[14], self.w.unitRequests[1].params[15]), (3, 3))
        self.c.RunNow()
        self.assertEqual(len(self.w.unitRequests), 1)

    def test_safe_origin_free_target_threat_is_rechecked_after_enemy_leaves(self):
        self.target_threat_geometry()
        self.check_target_threat_then_removal()

    def test_occupied_safe_alternative_cannot_bypass_unsafe_free_target(self):
        self.target_threat_geometry(occupied_alternative=True)
        self.check_target_threat_then_removal()


class LateCivilianOverlapLua51Tests(LateCivilianOverlapTests):
    runtime = Lua51


if __name__ == '__main__':
    unittest.main()
