"""Controller-level threatened overlap parking, preserving pending work and armies."""
from pathlib import Path
import sys,unittest
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tests'))
from lupa.lua51 import LuaRuntime as Lua51
from lupa.lua53 import LuaRuntime as Lua53
from gp_intent_harness import install_gp_bridge

class ThreatenedOverlapTests(unittest.TestCase):
    runtime=Lua53
    def setUp(self):
        self.lua=self.runtime(unpack_returned_tuples=True)
        self.lua.globals().print=lambda *args:None
        self.lua.execute((ROOT/'tests/lua/mock_world.lua').read_text(encoding='utf-8'))
        install_gp_bridge(self.lua)
        for name in ['tests/lua/mock_scientist.lua','tests/lua/mock_civilian_overlap.lua','mod/Baiqi/Lua/BaiqiConfig.lua','mod/Baiqi/Lua/BaiqiPolicy.lua','mod/Baiqi/Lua/BaiqiPlanner.lua','mod/Baiqi/Lua/BaiqiSettlementJournal.lua']:
            self.lua.execute((ROOT/name).read_text(encoding='utf-8'))
        self.lua.execute(r'''
local w,o=TestWorld,TestWorld.objects
w.secondCivilian=true;w.overlap=false;w.allowWait=false;w.evacCanChecks=0
local collection=o.player:GetUnits();local mover=assert(collection:FindID(4));local other=assert(collection:FindID(7));w.evacMover=mover;w.evacOther=other
for _,u in ipairs({mover,other})do
 u.IsReadyToSelect=function()return w.scientistReady~=false end
 u.IsDead=function()return w.evacDead==true end
 u.IsDelayedDeath=function()return w.evacDelayed==true end
 u.HasPendingOperations=function()if w.evacPendingUnknown then return nil end;return w.evacPending==true end
 u.GetBuildCharges=function()return 3 end
end
ActivityTypes.ACTIVITY_AWAKE=1797587246
UnitManager.GetActivityType=function()return w.evacActivity or ActivityTypes.ACTIVITY_AWAKE end
GameInfo.UnitOperations=GameInfo.UnitOperations or{}
GameInfo.UnitOperations.UNITOPERATION_SKIP_TURN={Hash=UnitOperationTypes.SKIP_TURN}
local J=BaiqiSettlementJournal;w.evacBank=assert(J.New(7))
local origin,target=Map.GetPlotByIndex(42),Map.GetPlotByIndex(43)
local function cell(i,x,y,owner)return{GetIndex=function()return i end,GetX=function()return x end,GetY=function()return y end,GetOwner=function()return owner or 7 end,IsWater=function()return false end,IsImpassable=function()return false end}end
local cells={[42]=origin,[43]=target,[45]=cell(45,0,3,8),[46]=cell(46,5,3,8)}
Map.GetPlotByIndex=function(i)return cells[i]end
Map.GetPlot=function(x,y)for _,p in pairs(cells)do if p:GetX()==x and p:GetY()==y then return p end end end
Map.GetPlotDistance=function(x,y,xx,yy)return math.abs(x-xx)+math.abs(y-yy)end
Map.GetPlotXYWithRangeCheck=function(x,y,dx,dy,r)if math.abs(dx)+math.abs(dy)<=r then return Map.GetPlot(x+dx,y+dy)end end
Map.GetAdjacentPlot=function(x,y,d)if x==2 and y==3 and d==0 then return target end end
local hostile={GetID=function()return 99 end,GetOwner=function()return 8 end,GetUnitType=function()return 1 end,GetX=function()return 0 end,GetY=function()return 3 end,GetFormationUnitCount=function()return 1 end}
local farther=setmetatable({GetID=function()return 100 end,GetX=function()return 5 end},{__index=hostile})
local originalUnits=Units.GetUnitsInPlot
Units.GetUnitsInPlot=function(p)
 if p:GetIndex()==45 then return w.evacThreat and{hostile}or{}end
 if p:GetIndex()==46 then return w.evacTargetThreat and{farther}or{}end
 return originalUnits(p)
end
o.player.GetDiplomacy=function()return{IsAtWarWith=function(_,owner)if w.evacWarShapeUnknown then return 'UNKNOWN' end;return owner==8 end}end
local originalCan=UnitManager.CanStartOperation
UnitManager.CanStartOperation=function(u,op,...)
 local result=originalCan(u,op,...)
 if op==UnitOperationTypes.MOVE_TO then w.evacCanChecks=w.evacCanChecks+1;if w.onEvacCan then w.onEvacCan()end end
 return result
end
''')
        controller=(ROOT/'mod/Baiqi/Lua/BaiqiController.lua').read_text(encoding='utf-8')
        self.lua.execute(controller+r'''
function TestEvacFixtureEvaluateIdle()
 local ctx,p=PlayerContext();assert(ctx and ctx.player==7)
 for _,u in p:GetUnits():Members()do unitEvaluated[UnitKey(u)]=u:GetID()==4 and true or 'native_wait' end
end
local function snapshot(pid)return 'READY',assert(BaiqiSettlementJournal.Clone(TestWorld.evacBank,pid))end
ExposedMembers.BaiqiSettlementIntentBridge={version=1,marker='baiqi-settlement-intent-v1',Initialize=snapshot,Snapshot=snapshot}
''')
        self.w=self.lua.globals().TestWorld;self.c=self.lua.globals().BaiqiController
        self.c.RunNow()
        self.assertEqual(len(self.w.unitRequests),0,'Priming fixture must not issue a game operation')
        self.lua.execute("TestWorld.scientistType=2;TestWorld.evacOther.GetUnitType=function()return 2 end;TestWorld.overlap=true;TestWorld.evacThreat=true;TestEvacFixtureEvaluateIdle()")

    def requests(self):
        return [(r.unit,r.op)for r in self.w.unitRequests.values()]

    def test_builder_escapes_known_hostile_origin_to_safe_empty_owned_adjacent_land_once(self):
        self.c.RunNow();self.c.RunNow()
        self.assertEqual(self.requests(),[(4,10)])
        self.assertEqual((self.w.unitRequests[1].params[14],self.w.unitRequests[1].params[15]),(3,3))
        self.assertEqual((self.w.scientistPlot,self.w.scientistMoves),(42,2),'Recording native request does not simulate arrival')

    def test_settler_with_ready_empty_journal_uses_same_bounded_safe_escape(self):
        self.lua.execute('TestWorld.scientistType=1;TestEvacFixtureEvaluateIdle()')
        self.c.RunNow()
        self.assertEqual(self.requests(),[(4,10)])

    def test_unknown_queued_pending_escort_dead_or_inactive_never_gets_escape(self):
        changes=['TestWorld.scientistFormation=2','TestWorld.queuedDestination=43','TestWorld.evacPending=true','TestWorld.evacPendingUnknown=true','UnitManager.GetQueuedDestination=function()return nil,nil end','UnitManager.GetQueuedDestination=nil','TestWorld.evacDead=true','TestWorld.evacDelayed=true','TestWorld.scientistReady=false','TestWorld.scientistMoves=0','TestWorld.evacActivity=77','TestWorld.strategic=false','TestWorld.busy=true','TestWorld.scientistType=0;TestEvacFixtureEvaluateIdle()']
        for change in changes:
            with self.subTest(change=change):
                self.setUp();self.lua.execute(change);self.c.RunNow();self.assertEqual(self.requests(),[])

    def test_destination_foreign_hidden_unsafe_occupied_or_bad_path_never_gets_escape(self):
        changes=['TestWorld.foreignTarget=true','TestWorld.hiddenTarget=true','TestWorld.evacTargetThreat=true','TestWorld.civilianTarget=true','TestWorld.occupiedTarget=true','TestWorld.foreignOccupant=true','TestWorld.water=true','TestWorld.impassable=true','TestWorld.noPath=true','TestWorld.rejectMove=true','UnitManager.GetMoveToPathEx=function()return{plots={42,99,43}}end']
        for change in changes:
            with self.subTest(change=change):
                self.setUp();self.lua.execute(change);self.c.RunNow();self.assertEqual(self.requests(),[])

    def test_unknown_origin_or_no_primary_civilian_overlap_never_grants_escape(self):
        changes=['TestWorld.evacWarShapeUnknown=true','TestWorld.overlap=false','TestWorld.armyOnly=true',"local old=Units.GetUnitsInPlotLayerID;Units.GetUnitsInPlotLayerID=function(p,...)if p:GetIndex()==45 then return nil end;return old(p,...)end"]
        for change in changes:
            with self.subTest(change=change):
                self.setUp();self.lua.execute(change);self.c.RunNow();self.assertEqual(self.requests(),[])

    def test_late_native_qualification_rechecks_pending_formation_target_and_bindings(self):
        changes=['TestWorld.evacPending=true','TestWorld.queuedDestination=43','TestWorld.scientistFormation=2','TestWorld.evacTargetThreat=true','TestWorld.occupiedTarget=true','UnitManager.RequestOperation=function()error("Changed writer must never run")end']
        for change in changes:
            with self.subTest(change=change):
                self.setUp();self.lua.execute('TestWorld.onEvacCan=function() '+change+' end');self.c.RunNow();self.assertEqual(self.requests(),[]);self.assertGreater(self.w.evacCanChecks,0,'Native qualification must be reached to test its changed-state boundary')

    def test_native_wait_and_armed_settlement_remain_held(self):
        # Only a real ARMED record, not a boolean pretending to be an intent.
        self.lua.execute("""TestWorld.scientistType=1;local J=BaiqiSettlementJournal;local bank=J.New(7);bank.serial=1;bank.operations['4']={unitID=4,unitType='UNIT_SETTLER',sequence=1,token=J.Token(7,1),turn=TestWorld.turn,requestID='7:1:1',stage='ARMED',empty=true,conflictingCity=false,plot=43,x=3,y=3};assert(J.Validate(bank,7));TestWorld.evacBank=bank;TestEvacFixtureEvaluateIdle()""")
        self.c.RunNow();self.assertEqual(self.requests(),[])

class ThreatenedOverlapLua51Tests(ThreatenedOverlapTests):
    runtime=Lua51

if __name__=='__main__':unittest.main()
