import unittest
import test_baiqi_naturalist_ui as harness


class NaturalistDetourTests(unittest.TestCase):
    setUp = harness.NaturalistUITests.setUp
    tearDown = harness.NaturalistUITests.tearDown

    def fixture(self):
        self.lua.execute('''
          local W=TestWorld
          local xy={[42]={16,15},[43]={16,14},[44]={15,14},[45]={15,15}}
          local plots={}
          for id,coords in pairs(xy) do
            plots[id]={GetIndex=function() return id end,GetX=function() return coords[1] end,
              GetY=function() return coords[2] end,GetFeatureType=function() return -1 end,
              GetOwner=function() return id==45 and W.foreignAlt and 8 or 7 end,
              IsWater=function() return id==45 and W.waterAlt==true end,
              IsImpassable=function() return id==45 and W.impassableAlt==true end,
              IsNationalPark=function() return false end}
          end
          Map.GetPlotByIndex=function(id) return plots[id] end
          Map.GetPlot=function(x,y)
            for id,p in pairs(plots) do if p:GetX()==x and p:GetY()==y then return p end end
          end
          Map.GetPlotDistance=function(x,y,a,b)
            if W.noProgress and x==15 and y==15 and a==15 and b==14 then return 2 end
            return math.abs(x-a)+math.abs(y-b)
          end
          Map.GetAdjacentPlot=function(x,y,direction)
            if x==16 and y==15 then return direction==0 and plots[43] or direction==1 and plots[45] or nil end
          end
          W.objects.missionary.GetX=function() return plots[W.missionaryPlot]:GetX() end
          W.objects.missionary.GetY=function() return plots[W.missionaryPlot]:GetY() end
          W.parkCandidates={44};W.blocked=true
          GameInfo.Units[70]={UnitType='UNIT_GREAT_MUSICIAN',FormationClass='FORMATION_CLASS_CIVILIAN'}
          local occupant={GetID=function() return 99 end,GetOwner=function() return 7 end,
            GetUnitType=function() return W.unknownOccupant and 71 or W.militaryOccupant and 0 or 70 end}
          Units.GetUnitsInPlot=function(p)
            if (p:GetIndex()==43 and W.blocked) or (p:GetIndex()==45 and W.detourBlocked) then return {occupant} end
            return {}
          end
          PlayersVisibility[7].IsVisible=function(_,x,y) return not (W.hideAlt and x==15 and y==15) end
          UnitManager.GetMoveToPathEx=function(unit,target)
            W.pathTargets[#W.pathTargets+1]=target
            if W.noPath then return nil end
            return {plots={42,43,44}}
          end
        ''')

    def moves(self):
        return [r for r in self.w.unitRequests.values() if r.op == self.lua.globals().UnitOperationTypes.MOVE_TO]

    def test_occupied_native_legal_step_uses_one_path_and_empty_detour(self):
        self.fixture()
        self.c.RunNow()
        moves = self.moves()
        self.assertEqual(list(self.w.pathTargets.values()), [44], self.logs)
        self.assertEqual(len(moves), 1, self.logs)
        keys = self.lua.globals().UnitOperationTypes
        self.assertEqual((moves[0].unit, moves[0].params[keys.PARAM_X], moves[0].params[keys.PARAM_Y]), (4,15,15))
        self.assertEqual(len(self.w.parkRequests), 0)
        self.assertTrue(all(r.unit == 4 for r in self.w.unitRequests.values()))

    def test_late_detour_occupancy_after_qualification_prevents_move(self):
        self.fixture()
        self.lua.execute('''
          local can=UnitManager.CanStartOperation
          UnitManager.CanStartOperation=function(unit,op,...)
            if op==UnitOperationTypes.MOVE_TO then TestWorld.detourBlocked=true end
            return can(unit,op,...)
          end
        ''')
        self.c.RunNow()
        self.assertEqual(len(self.moves()), 0, self.logs)
        self.assertEqual(list(self.w.pathTargets.values()), [44])

    def test_missing_original_path_does_not_scan_or_move_detour(self):
        self.fixture()
        self.w.noPath = True
        self.lua.execute("Map.GetAdjacentPlot=function() error('No detour without a safe original path') end")
        self.c.RunNow()
        self.assertEqual(len(self.moves()), 0, self.logs)
        self.assertEqual(list(self.w.pathTargets.values()), [44])

    def test_detour_requires_visible_owned_passable_strict_progress(self):
        for key in ('foreignAlt','hideAlt','waterAlt','impassableAlt','noProgress'):
            with self.subTest(key=key):
                self.setUp()
                self.fixture()
                self.w[key] = True
                self.c.RunNow()
                self.assertEqual(len(self.moves()), 0, self.logs)
                self.assertEqual(list(self.w.pathTargets.values()), [44])

    def test_unknown_occupant_does_not_authorize_a_detour(self):
        self.fixture()
        self.w.unknownOccupant = True
        self.c.RunNow()
        self.assertEqual(len(self.moves()), 0, self.logs)

    def test_friendly_military_does_not_block_or_receive_commands(self):
        self.fixture()
        self.w.militaryOccupant = True
        self.c.RunNow()
        moves = self.moves()
        self.assertEqual(len(moves), 1, self.logs)
        keys = self.lua.globals().UnitOperationTypes
        self.assertEqual((moves[0].unit, moves[0].params[keys.PARAM_X], moves[0].params[keys.PARAM_Y]), (4,16,14))
        self.assertTrue(all(r.unit == 4 for r in self.w.unitRequests.values()))


if __name__ == '__main__':
    unittest.main()
