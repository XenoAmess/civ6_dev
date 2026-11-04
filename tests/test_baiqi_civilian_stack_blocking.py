import unittest
import test_baiqi_controller as module


class BaiqiCivilianStackBlockingTests(unittest.TestCase):
    def setUp(self):
        module.BaiqiControllerTests.setUp(self)
        module.BaiqiControllerTests.movement(self)
        self.w, self.c = self.world, self.controller
        self.lua.execute("""
local w=TestWorld
GameInfo.Units[77]={UnitType='UNIT_GREAT_MERCHANT',Index=77,Hash=777,FormationClass='FORMATION_CLASS_CIVILIAN'}
GameInfo.Units[0].FormationClass='FORMATION_CLASS_LAND_COMBAT'
GameInfo.Units[61]={UnitType='UNIT_APOSTLE',Index=61,Hash=661,FormationClass='FORMATION_CLASS_CIVILIAN'}
local function occupant(id,kind)
 return {GetID=function()return id end,GetOwner=function()return 7 end,GetUnitType=function()return kind end,
  GetX=function()return 3 end,GetY=function()return 3 end}
end
local merchant,army,apostle=occupant(4194337,77),occupant(200,0),occupant(61,61)
local primary=Units.GetUnitsInPlot
Units.GetUnitsInPlot=function(plot)
 if plot:GetIndex()==43 then
  if w.targetOccupied then return {merchant} end
  if w.targetArmy then return {army} end
 end
 return primary(plot)
end
local religious=Units.GetUnitsInPlotLayerID
Units.GetUnitsInPlotLayerID=function(plot,layer)
 assert(layer==MapLayers.RELIGIOUS,'Background read a private map layer')
 if plot:GetIndex()==43 and w.religiousTarget then return {apostle} end
 return religious(plot,layer)
end
""")

    def test_primary_civilian_stack_blocks_move(self):
        self.w.targetOccupied = True
        self.w.targetArmy = False
        self.w.religiousTarget = False
        self.c.RunNow()
        requests = list(self.w.unitRequests.values())
        self.assertEqual([(r.unit, r.op) for r in requests], [(3, 17)])
        self.assertTrue(all(r.unit == 3 for r in requests))

    def test_primary_army_stack_allows_move(self):
        self.w.targetOccupied = False
        self.w.targetArmy = True
        self.w.religiousTarget = False
        self.c.RunNow()
        requests = list(self.w.unitRequests.values())
        self.assertEqual(len(requests), 1)
        self.assertEqual(requests[0].unit, 3)
        self.assertEqual(requests[0].op, 10)
        self.assertEqual(requests[0].params[14], 3)
        self.assertEqual(requests[0].params[15], 3)

    def test_religious_civilian_does_not_block_primary_move(self):
        self.w.targetOccupied = False
        self.w.targetArmy = False
        self.w.religiousTarget = True
        self.c.RunNow()
        requests = list(self.w.unitRequests.values())
        self.assertEqual(len(requests), 1)
        self.assertEqual(requests[0].unit, 3)
        self.assertEqual(requests[0].op, 10)
        self.assertEqual(requests[0].params[14], 3)
        self.assertEqual(requests[0].params[15], 3)
        # Verify no orders were sent to the apostle
        self.assertEqual(len([r for r in requests if r.unit == 61]), 0)


import test_baiqi_path_ranking as ranking
import test_baiqi_builder_route_phases as phases

def occupy_first_step(lua):
    lua.execute("""
GameInfo.Units[77]={UnitType='UNIT_GREAT_MERCHANT',Index=77,Hash=777,FormationClass='FORMATION_CLASS_CIVILIAN'}
local merchant={GetID=function()return 4194337 end,GetOwner=function()return 7 end,GetUnitType=function()return 77 end}
local previous=Units.GetUnitsInPlot
Units.GetUnitsInPlot=function(plot) if plot:GetIndex()==43 then return {merchant} end;return previous(plot) end
""")

class BuilderPrimaryStackPlanningTests(unittest.TestCase):
    setUp = ranking.PathRankingTests.setUp

    def test_blocked_first_step_checks_next_native_hint_before_write(self):
        occupy_first_step(self.lua)
        self.lua.execute('TestWorld.builderRecommendations={43,44}')
        self.c.RunNow()
        self.assertEqual(len(self.w.unitRequests), 0)
        self.c.RunNow()
        actual = list(self.w.unitRequests.values())
        self.assertEqual([(a.unit, a.op, a.params[14], a.params[15]) for a in actual], [(3,10,2,4)])
        self.assertEqual([(a.unit,a.target) for a in self.w.pathQueries.values()], [(3,43),(3,44)])

class BuilderPrimaryStackPhaseTests(unittest.TestCase):
    setUp = phases.BuilderRoutePhaseTests.setUp
    moves = phases.BuilderRoutePhaseTests.moves

    def test_phased_blocked_step_falls_back_without_submitting_or_requerying_it(self):
        occupy_first_step(self.lua)
        self.lua.execute('TestWorld.builderRecommendations={43,44}')
        for _ in range(8):
            self.c.RunNow()
        self.assertEqual([(a.unit,a.params[14],a.params[15]) for a in self.moves()], [(3,2,4)])
        self.assertEqual([(a.unit,a.target) for a in self.w.pathQueries.values()], [(3,43),(3,44)])
        self.assertTrue(all(a.unit == 3 for a in self.w.unitRequests.values()))

    def test_new_primary_occupant_after_validation_is_blocked_at_final_write(self):
        phases.BuilderRoutePhaseTests.query_then_validate(self)
        occupy_first_step(self.lua)
        self.c.RunNow()
        self.assertEqual(self.moves(), [])
        self.assertEqual([(a.unit,a.op) for a in self.w.unitRequests.values()], [(3,17)])
        self.assertEqual([(a.unit,a.target) for a in self.w.pathQueries.values()], [(3,43)])
