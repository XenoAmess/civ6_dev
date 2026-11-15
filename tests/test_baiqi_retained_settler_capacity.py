"""Independent production must not replay or erase a retained founding request."""
from pathlib import Path
import unittest
from lupa.lua53 import LuaRuntime

ROOT = Path(__file__).resolve().parents[1]


class RetainedSettlerCapacityTests(unittest.TestCase):
    def setUp(self):
        self.lua = LuaRuntime(unpack_returned_tuples=True)
        for name in (
            "tests/lua/mock_world.lua", "tests/lua/mock_trade.lua",
            "tests/lua/mock_military.lua", "mod/Baiqi/Lua/BaiqiConfig.lua",
            "mod/Baiqi/Lua/BaiqiPolicy.lua", "mod/Baiqi/Lua/BaiqiPlanner.lua",
            "mod/Baiqi/Lua/BaiqiController.lua",
        ):
            self.lua.execute((ROOT / name).read_text(encoding="utf-8"))
        self.lua.execute("""
local w=TestWorld;local o=w.objects
w.turn=2;w.armyTypes={1};w.allowedMilitary={[201]=true};w.allowProject=true
w.EnableSettlerSite()
o.army.GetX=function()return 8 end;o.army.GetY=function()return 3 end
o.army.GetPlotId=function()return 44 end
o.army.GetDamage=function()return w.unitDamage or 0 end
o.army.HasPendingOperations=function()return w.actorPending==true end
local alternative={GetIndex=function()return 45 end,GetX=function()return 7 end,GetY=function()return 3 end,
 GetOwner=function()return -1 end,GetFeatureType=function()return -1 end,
 IsWater=function()return false end,IsImpassable=function()return false end,IsCity=function()return false end}
local oldIndex,oldPlot=Map.GetPlotByIndex,Map.GetPlot
Map.GetPlotByIndex=function(i)if i==45 then return alternative end;return oldIndex(i)end
Map.GetPlot=function(x,y)if x==7 and y==3 then return alternative end;return oldPlot(x,y)end
w.settlementRecommendations={{SettlingLocation=44},{SettlingLocation=45}}
local J=BaiqiSettlementJournal;local bank=J.New(7);bank.serial=1
bank.operations['101']={unitID=101,unitType='UNIT_SETTLER',sequence=1,token=J.Token(7,1),
 turn=1,requestID='7:1:1',stage='ARMED',empty=true,conflictingCity=false,plot=44,x=8,y=3}
w.settlementBank=bank;w.originalBank=J.Clone(bank,7)
BaiqiController.SetSettlementLoadKind(true)
""")
        self.w = self.lua.globals().TestWorld
        self.c = self.lua.globals().BaiqiController

    def units(self):
        return [r.params[4] for r in self.w.cityRequests.values()
                if r.params[4] is not None]

    def run_and_preserve(self, count=2):
        for _ in range(count):
            self.c.RunNow()
        self.assertEqual(len(self.w.unitRequests), 0, "Retained actor received an order")
        self.lua.execute("assert(BaiqiSettlementJournal.Equal(TestWorld.originalBank,TestWorld.settlementBank,7))")

    def test_one_replacement_and_unacknowledged_commitment_close_other_city(self):
        self.run_and_preserve(3)
        self.assertEqual(self.units(), [201])
        self.assertEqual(self.w.cityRequests[2].params[5], 301)

    def test_native_queue_ack_is_not_counted_as_another_available_slot(self):
        self.run_and_preserve(1)
        self.lua.execute("TestWorld.queues[66]={{UnitType=1}}")
        self.c.RefreshProduction()
        self.run_and_preserve(2)
        self.assertEqual(self.units(), [201])

    def test_new_live_settler_closes_allowance(self):
        self.lua.execute("TestWorld.armyTypes={1,1}")
        self.run_and_preserve()
        self.assertEqual(self.units(), [])

    def test_second_unresolved_record_even_without_live_actor_closes_allowance(self):
        self.lua.execute("""
local w=TestWorld;local J=BaiqiSettlementJournal;local b=w.settlementBank;b.serial=2
b.operations['999']={unitID=999,unitType='UNIT_SETTLER',sequence=2,token=J.Token(7,2),
 turn=1,requestID='7:1:2',stage='ARMED',empty=true,conflictingCity=false,plot=45,x=7,y=3}
w.originalBank=J.Clone(b,7)
""")
        self.run_and_preserve()
        self.assertEqual(self.units(), [])

    def test_only_old_held_goal_does_not_justify_new_production(self):
        self.lua.execute("TestWorld.settlementRecommendations={{SettlingLocation=44}}")
        self.run_and_preserve()
        self.assertEqual(self.units(), [])
        self.assertGreater(self.w.settlementQueries, 0)

    def enable_bounded_alternates(self):
        self.lua.execute("""
local w=TestWorld;local oldXY=Map.GetPlotXYWithRangeCheck
w.settlementRecommendations={{SettlingLocation=44}};w.alternateGeometryCalls=0
Map.GetPlotXYWithRangeCheck=function(x,y,dx,dy,r)
 if x==8 and y==3 and r==2 then
  w.alternateGeometryCalls=w.alternateGeometryCalls+1
  if w.overlargeGeometry and (dx~=0 or dy~=0)then
   local index=1000+(dx+2)*5+(dy+2)
   return {GetIndex=function()return index end,GetX=function()return x+dx end,GetY=function()return y+dy end}
  end
  if dx==-1 and dy==0 then return Map.GetPlotByIndex(45)end
 end
 return oldXY(x,y,dx,dy,r)
end
""")

    def test_sole_protected_hint_uses_bounded_alternate_without_old_orders(self):
        self.enable_bounded_alternates()
        self.run_and_preserve(3)
        self.assertEqual(self.units(), [201])
        self.assertGreater(self.w.alternateGeometryCalls, 0)

    def test_no_protected_hint_does_not_search_alternates(self):
        self.enable_bounded_alternates()
        self.lua.execute("TestWorld.settlementRecommendations={}")
        self.run_and_preserve()
        self.assertEqual(self.units(), [])
        self.assertEqual(self.w.alternateGeometryCalls, 0)

    def test_native_alternative_keeps_original_priority_without_fallback_scan(self):
        self.enable_bounded_alternates()
        self.lua.execute("TestWorld.settlementRecommendations={{SettlingLocation=44},{SettlingLocation=45}}")
        self.run_and_preserve()
        self.assertEqual(self.units(), [201])
        self.assertEqual(self.w.alternateGeometryCalls, 0)

    def test_hidden_alternate_metadata_is_not_read(self):
        self.enable_bounded_alternates()
        self.lua.execute("""
local vis=PlayersVisibility[7]
vis.IsVisible=function(self,x,y)return x~=7 end
local plot=Map.GetPlotByIndex(45)
plot.GetOwner=function()error('HIDDEN_METADATA_READ')end
""")
        self.run_and_preserve()
        self.assertEqual(self.units(), [])
        self.assertNotIn("脚本错误", self.c.GetStatus())

    def test_fallback_exception_discards_partial_proposals_and_other_work_continues(self):
        self.enable_bounded_alternates()
        self.lua.execute("""
local seenAlternative=false;local vis=PlayersVisibility[7]
vis.IsVisible=function(self,x,y)
 if x==7 and y==3 then seenAlternative=true;return true end
 if seenAlternative and x==8 and y==3 then
  TestWorld.afterProposalThrows=(TestWorld.afterProposalThrows or 0)+1;error('AFTER_FIRST_PROPOSAL')
 end
 return true
end
""")
        self.run_and_preserve()
        self.assertEqual(self.units(), [])
        self.assertEqual(len(self.w.cityRequests), 2)
        self.assertGreater(self.w.afterProposalThrows, 0)
        self.assertNotIn("脚本错误", self.c.GetStatus())

    def test_more_than_nineteen_geometry_cells_declines_alternates(self):
        self.enable_bounded_alternates()
        self.w.overlargeGeometry = True
        self.run_and_preserve()
        self.assertEqual(self.units(), [])
        self.assertGreater(self.w.alternateGeometryCalls, 19)
        self.assertNotIn("脚本错误", self.c.GetStatus())

    def test_fallback_rechecks_live_native_hint_before_production_dispatch(self):
        self.enable_bounded_alternates()
        self.w.loseSettlementSite = True
        self.run_and_preserve()
        self.assertEqual(self.units(), [])
        self.assertGreater(self.w.settlementQueries, 1)

    def test_alternate_feature_and_city_distance_guards_still_apply(self):
        for condition in ("feature", "city_distance"):
            with self.subTest(condition=condition):
                self.setUp()
                self.enable_bounded_alternates()
                if condition == "feature":
                    self.lua.execute("Map.GetPlotByIndex(45).GetFeatureType=function()return 999 end")
                else:
                    self.lua.execute("""
local old=Map.GetPlotDistance
Map.GetPlotDistance=function(x,y,cx,cy)if x==7 and cx==2 then return 2 end;return old(x,y,cx,cy)end
""")
                self.run_and_preserve()
                self.assertEqual(self.units(), [])

    def test_alternative_site_disappears_before_dispatch(self):
        self.w.loseSettlementSite = True
        self.run_and_preserve()
        self.assertEqual(self.units(), [])

    def test_validated_budget_closes_when_actor_queue_changes(self):
        self.lua.execute("""
local checks=0
CityManager.CanStartOperation=function(city,op,params)
 if params[CityOperationTypes.PARAM_UNIT_TYPE]==201 then
  checks=checks+1;if checks==2 then TestWorld.queuedDestination=44 end
 end
 return true
end
""")
        self.run_and_preserve()
        self.assertEqual(self.units(), [])

    def test_escort_has_no_allowance_and_no_indirect_army_order(self):
        self.w.formation = 2
        self.run_and_preserve()
        self.assertEqual(self.units(), [])

    def test_new_unknown_between_candidate_and_dispatch_closes_cached_allowance(self):
        self.lua.execute("""
local checks=0
CityManager.CanStartOperation=function(city,op,params)
 if params[CityOperationTypes.PARAM_UNIT_TYPE]==201 then
  checks=checks+1
  if checks==2 then
   local J=BaiqiSettlementJournal;local b=TestWorld.settlementBank;b.serial=2
   b.operations['999']={unitID=999,unitType='UNIT_SETTLER',sequence=2,token=J.Token(7,2),
    turn=1,requestID='7:1:2',stage='ARMED',empty=true,conflictingCity=false,plot=45,x=7,y=3}
  end
 end
 return true
end
""")
        self.c.RunNow()
        self.assertEqual(self.units(), [])
        self.assertEqual(len(self.w.unitRequests), 0)
        self.assertEqual(self.w.settlementBank.operations["101"].token, "settle:7:1")
        self.assertEqual(self.w.settlementBank.operations["999"].stage, "ARMED")

    def test_fresh_snapshot_unavailability_or_change_closes_dispatch(self):
        for flavor in ("unavailable", "throw", "owner", "token", "observed"):
            with self.subTest(flavor=flavor):
                self.setUp()
                self.w.snapshotFlavor = flavor
                self.lua.execute("""
local w=TestWorld;local b=ExposedMembers.BaiqiSettlementIntentBridge
local old=b.Snapshot;local checks=0
b.Snapshot=function(...)
 local status,bank,reason=old(...)
 if not w.changeSnapshot then return status,bank,reason end
 if w.snapshotFlavor=='unavailable'then return 'UNAVAILABLE' end
 if w.snapshotFlavor=='throw'then error('READ_UNAVAILABLE')end
 if w.snapshotFlavor=='owner'then bank.owner=8
 elseif w.snapshotFlavor=='token'then
  bank.serial=2;local op=bank.operations['101'];op.sequence=2;op.token='settle:7:2';op.requestID='7:1:2'
 elseif w.snapshotFlavor=='observed'then
  local op=bank.operations['101'];op.stage='OBSERVED';op.cityID=66
 end
 return status,bank,reason
end
CityManager.CanStartOperation=function(city,op,params)
 if params[CityOperationTypes.PARAM_UNIT_TYPE]==201 then
  checks=checks+1;if checks==2 then w.changeSnapshot=true end
 end
 return true
end
""")
                self.run_and_preserve()
                self.assertEqual(self.units(), [])

    def test_pending_actor_does_not_open_spare_capacity(self):
        self.w.actorPending = True
        self.run_and_preserve()
        self.assertEqual(self.units(), [])

    def test_native_destination_prevents_capacity_without_cancel(self):
        self.w.queuedDestination = 44
        self.run_and_preserve()
        self.assertEqual(self.units(), [])

    def test_damaged_actor_keeps_original_capacity(self):
        self.w.unitDamage = 1
        self.run_and_preserve()
        self.assertEqual(self.units(), [])

    def test_full_id_alias_is_not_a_retained_actor(self):
        self.lua.execute("""
local p=TestWorld.objects.player;local old=p.GetUnits
p.GetUnits=function(self)local list=old(self);list.FindID=function()
 return setmetatable({GetID=function()return 900 end},{__index=TestWorld.objects.army})end;return list end
""")
        self.run_and_preserve()
        self.assertEqual(self.units(), [])

    def test_same_turn_record_does_not_open_capacity(self):
        self.lua.execute("""
TestWorld.settlementBank.operations['101'].turn=2
TestWorld.settlementBank.operations['101'].requestID='7:2:1'
TestWorld.originalBank=BaiqiSettlementJournal.Clone(TestWorld.settlementBank,7)
""")
        self.run_and_preserve()
        self.assertEqual(self.units(), [])

    def test_unvalidated_bank_never_opens_capacity(self):
        self.lua.execute("TestWorld.settlementBank.owner=8")
        self.c.RunNow()
        self.assertEqual(self.units(), [])
        self.assertEqual(len(self.w.unitRequests), 0)

    def test_ordinary_config_two_keeps_its_existing_live_limit(self):
        self.lua.execute("BaiqiConfig.maxSettlers=2")
        self.run_and_preserve()
        self.assertEqual(self.units(), [201])

    def test_pure_planner_rejects_unknown_and_malformed_capacity_counts(self):
        self.lua.execute("""
local P=BaiqiPlanner;local C=BaiqiConfig
local s={gold=100,netGold=6,cities=2,maintenance=0,committedMaintenance=0,
 resourceAffordable=true,cityPopulation=4,settlers=1,queuedSettlers=0,reservedSettlers=0,hasSafeSite=true}
assert(P.AllowRecruit('settler',s,C)==false)
s.retainedSettlers=1;assert(P.AllowRecruit('settler',s,C)==true)
for _,key in ipairs({'settlers','queuedSettlers','reservedSettlers'})do
 local old=s[key]
 for _,value in ipairs({-1,0.5,true,'1',math.huge})do s[key]=value;assert(P.AllowRecruit('settler',s,C)==false)end
 s[key]=nil;assert(P.AllowRecruit('settler',s,C)==false);s[key]=old
end
s.retainedSettlers=true;assert(P.AllowRecruit('settler',s,C)==false)
s.retainedSettlers=1;s.gold=99;assert(P.AllowRecruit('settler',s,C)==false)
s.gold=100;s.netGold=1;assert(P.AllowRecruit('settler',s,C)==false)
s.netGold=6;s.cityPopulation=3;assert(P.AllowRecruit('settler',s,C)==false)
s.cityPopulation=4;s.resourceAffordable=false;assert(P.AllowRecruit('settler',s,C)==false)
""")


if __name__ == "__main__":
    unittest.main()
