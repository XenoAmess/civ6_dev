"""Real Controller ranks district hints before querying native GP paths."""
import unittest
import test_baiqi_scientist as fixture


class GreatPersonPathTests(unittest.TestCase):
    def setUp(self):
        fixture.BaiqiScientistTests.setUp(self)
        self.lua.execute('''
local w=TestWorld
w.pathRequests={};w.targets={45,44,43};w.blocked={};w.hidden={};w.legal={};w.steps={}
local plots={}
local coords={[42]={2,3},[43]={3,3},[44]={2,4},[45]={4,3}}
for index,xy in pairs(coords) do
 plots[index]={GetIndex=function() return index end,GetX=function() return xy[1] end,
  GetY=function() return xy[2] end,GetOwner=function() return w.foreign==index and 8 or 7 end}
end
Map.GetPlotByIndex=function(index) return plots[index] end
Map.GetPlot=function(x,y)
 for _,plot in pairs(plots) do if plot:GetX()==x and plot:GetY()==y then return plot end end
end
local person=w.objects.player:GetUnits():FindID(4)
person.GetX=function() return plots[w.scientistPlot]:GetX() end
person.GetY=function() return plots[w.scientistPlot]:GetY() end
Map.GetPlotDistance=function(x,y,x2,y2) return math.abs(x-x2)+math.abs(y-y2) end
PlayersVisibility[7].IsRevealed=function(_,x,y) return not w.hidden[Map.GetPlot(x,y):GetIndex()] end
Map.GetPlotXYWithRangeCheck=function(x,y,dx,dy) if dx==0 and dy==0 then return Map.GetPlot(x,y) end end
function w.objects.player:GetCities()
 local cities={}
 for i,index in ipairs(w.targets) do
  local plot=plots[index]
  local city=setmetatable({GetID=function() return 66+i end,
   GetDistricts=function() return {HasDistrict=function() return true end,
    Members=function() local done=false;return function()
     if done then return end;done=true
     return 1,{GetType=function() return 7 end,GetX=function() return plot:GetX() end,GetY=function() return plot:GetY() end}
    end end} end},{__index=w.objects.city})
  cities[#cities+1]=city
 end
 return {Members=function() local i=0;return function() i=i+1;if cities[i] then return i,cities[i] end end end,
  GetCount=function() return #cities end}
end
UnitManager.GetMoveToPathEx=function(unit,index)
 assert(unit:GetID()==4)
 w.pathRequests[#w.pathRequests+1]=index
 if w.blocked[index] then return {plots={}} end
 local start=Map.GetPlot(unit:GetX(),unit:GetY()):GetIndex()
 if start==index then return {plots={start}} end
 local via=w.steps[index]
 if not via and start==42 and index==45 then via=43 end
 if not via and start==43 and index==44 then via=42 end
 return {plots=via and via~=start and via~=index and {start,via,index} or {start,index}}
end
UnitManager.CanStartCommand=function() return w.legal[w.scientistPlot]==true end
local original=UnitManager.CanStartOperation
UnitManager.CanStartOperation=function(unit,operation,...)
 if operation==UnitOperationTypes.MOVE_TO and w.rejectMove then return false end
 return original(unit,operation,...)
end
''')

    def paths(self):
        return list(self.w.pathRequests.values())

    def test_nearest_then_index_wins_even_when_hints_arrive_farther_first(self):
        self.c.RunNow()
        self.assertEqual(self.paths(), [43])
        self.assertEqual((self.w.unitRequests[1].params[14], self.w.unitRequests[1].params[15]), (3, 3))

    def test_duplicates_only_query_one_path_when_unreachable_before_fallback(self):
        self.lua.execute('TestWorld.targets={43,43,44};TestWorld.blocked[43]=true')
        self.c.RunNow()
        self.assertEqual(self.paths(), [43, 44])
        self.assertEqual((self.w.unitRequests[1].params[14], self.w.unitRequests[1].params[15]), (2, 4))

    def test_unrevealed_or_foreign_hints_never_query_native_paths(self):
        self.lua.execute('TestWorld.hidden[43]=true;TestWorld.foreign=44')
        self.c.RunNow()
        self.assertEqual(self.paths(), [45])

    def test_first_reachable_move_rejection_does_not_query_another_target(self):
        self.w.rejectMove = True
        self.c.RunNow()
        self.assertEqual(self.paths(), [43])
        self.assertEqual([r.op for r in self.w.unitRequests.values()], [17])

    def test_all_unreachable_wait_without_moving(self):
        self.lua.execute('TestWorld.blocked={[43]=true,[44]=true,[45]=true}')
        self.c.RunNow()
        self.assertEqual(self.paths(), [43, 44, 45])
        self.assertEqual([r.op for r in self.w.unitRequests.values()], [17])

    def test_armed_intent_skips_planning_and_fallback_unit_orders(self):
        self.w.scientistPlot = 43
        granted, _, _ = self.lua.globals().ExposedMembers.BaiqiGreatPersonIntentBridge.Prepare(
            7, 4, 'UNIT_GREAT_SCIENTIST', 5, 70, 1, 3, 3)
        self.assertTrue(granted)
        self.w.scientistPlot = 42
        self.c.RunNow()
        self.assertEqual(self.paths(), [])
        self.assertEqual(len(self.w.unitRequests), 0)

    def test_multi_step_destination_survives_turn_and_does_not_return_to_used_city(self):
        self.lua.execute('TestWorld.targets={42,45};TestWorld.steps[45]=43')
        self.c.RunNow()
        self.assertEqual(self.w.unitRequests[1].params[14], 3)
        self.w.scientistPlot, self.w.scientistMoves = 43, 0
        self.w.turn += 1
        self.w.scientistMoves = 2
        self.c.RunNow()
        self.assertEqual((self.w.unitRequests[2].params[14], self.w.unitRequests[2].params[15]), (4, 3))
        self.assertEqual(self.paths(), [45, 45])

    def test_pending_native_move_does_not_replan_before_arrival(self):
        self.lua.execute('TestWorld.targets={42,45};TestWorld.steps[45]=43')
        self.c.RunNow()
        self.w.queuedDestination = 43
        self.c.Update(1)
        self.c.RunNow()
        self.assertEqual((self.paths(), len(self.w.unitRequests)), ([45], 1))

    def test_arrival_activates_and_only_actual_decrease_allows_next_charge(self):
        self.lua.execute('TestWorld.targets={42,45};TestWorld.steps[45]=43;TestWorld.legal[45]=true')
        self.w.scientistCharges = 3
        self.c.RunNow()
        self.w.scientistPlot = 45
        self.c.Update(.35)
        self.assertEqual(len(self.w.commandRequests), 1)
        self.assertEqual(self.lua.globals().TestBridge.store.BAIQI_GREAT_PERSON_INTENTS_V1.operations['4'].charges, 3)
        self.w.scientistCharges = 2
        self.c.RunNow()
        self.assertEqual(len(self.w.commandRequests), 2)
        self.assertEqual(self.lua.globals().TestBridge.store.BAIQI_GREAT_PERSON_INTENTS_V1.operations['4'].sequence, 2)

    def test_native_illegal_current_city_is_skipped_without_querying_its_path(self):
        self.lua.execute('TestWorld.targets={42,45}')
        self.c.RunNow()
        self.assertEqual(self.paths(), [45])
        self.assertEqual(self.w.unitRequests[1].params[14], 3)

    def test_legal_current_city_with_budget_denial_does_not_choose_another_city(self):
        self.lua.execute('TestWorld.targets={42,45};TestWorld.legal[42]=true;BaiqiConfig.requestsPerTurn=0')
        self.c.RunNow()
        self.assertEqual((self.paths(), len(self.w.unitRequests), len(self.w.commandRequests)), ([], 0, 0))
        self.w.turn += 1
        self.lua.globals().BaiqiConfig.requestsPerTurn = 64
        self.c.RunNow()
        self.assertEqual(len(self.w.commandRequests), 1)

    def test_lost_ownership_or_reveal_invalidates_destination_instead_of_entering_it(self):
        for change in ('TestWorld.foreign=45', 'TestWorld.hidden[45]=true'):
            with self.subTest(change=change):
                self.setUp()
                self.lua.execute('TestWorld.targets={42,45,44};TestWorld.blocked[44]=true;TestWorld.steps[45]=43')
                self.c.RunNow()
                self.w.scientistPlot = 43
                self.lua.execute(change+';TestWorld.blocked[44]=false')
                self.w.turn += 1
                self.c.RunNow()
                self.assertEqual(self.paths(), [44, 45, 44])
                self.assertEqual((self.w.unitRequests[2].params[14], self.w.unitRequests[2].params[15]), (2, 3))

    def test_exhausted_wave_retries_when_conditions_change_on_later_turn(self):
        self.lua.execute('TestWorld.blocked={[43]=true,[44]=true,[45]=true}')
        self.c.RunNow()
        self.lua.execute('TestWorld.blocked={}')
        self.w.turn += 1
        self.c.RunNow()
        self.assertEqual(self.paths(), [43, 44, 45, 43])
        self.assertEqual(self.w.unitRequests[2].op, 10)

    def test_unreachable_committed_destination_tries_another_safe_city(self):
        self.lua.execute('TestWorld.targets={42,45};TestWorld.steps[45]=43')
        self.c.RunNow()
        self.w.scientistPlot = 43
        self.lua.execute('TestWorld.targets={42,44,45};TestWorld.blocked[45]=true')
        self.c.RunNow()
        self.assertEqual(self.paths(), [45, 45, 44])
        self.assertEqual((self.w.unitRequests[2].params[14], self.w.unitRequests[2].params[15]), (2, 3))


if __name__ == '__main__':
    unittest.main()
