"""An idle builder yields a native settler choke without any military order."""
from pathlib import Path
import unittest
from lupa.lua51 import LuaRuntime as Lua51
from lupa.lua53 import LuaRuntime as Lua53
import test_baiqi_settler_bounded_detour as bounded

ROOT=Path(__file__).resolve().parents[1]


class BuilderYieldTests(unittest.TestCase):
    def world(self,runtime,change=''):
        h=bounded.SettlerBoundedDetourTests('test_native_blockade_uses_qualified_step_away_from_goal')
        h.candidate_source=(ROOT/'mod/Baiqi/Lua/BaiqiController.lua').read_text(encoding='utf-8')+'''
function TestBuilderRouteWait()
 local ctx,player,state=PlayerContext();local u=player:GetUnits():FindID(3)
 return WaitBuilderRoute(ctx,player,state,u,{player=ctx.player,turn=turn,key=UnitKey(u)})
end
'''
        lua=h.world(runtime)
        lua.execute('''
local w,o=TestWorld,TestWorld.objects
ActivityTypes=ActivityTypes or{};ActivityTypes.ACTIVITY_AWAKE=1797587246
w.withBuilder=true;w.withSettler=true;w.builderPlot=274;w.settlerPlot=229
w.builderMoves=2;w.builderRecommendations={};w.yieldChecks=0
w.nativePath={229,274};for i=2,#FixturePath do w.nativePath[#w.nativePath+1]=FixturePath[i]end
for _,p in pairs(w.plots)do p.IsImprovementPillaged=function()return false end;p.GetImprovementType=function()return 0 end end
o.builder.GetX=function()return w.plots[w.builderPlot]:GetX()end
o.builder.GetY=function()return w.plots[w.builderPlot]:GetY()end
o.builder.GetPlotId=function()return w.builderPlot end
o.builder.GetFormationUnitCount=function()return w.builderFormation or 1 end
o.builder.GetBuildCharges=function()return 2 end
o.builder.IsReadyToMove=function()return w.builderReady~=false end
o.builder.IsReadyToSelect=o.builder.IsReadyToMove
o.builder.IsDead=function()return w.builderDead==true end
o.builder.IsDelayedDeath=function()return w.builderDelayed==true end
o.builder.HasPendingOperations=function()if w.pendingUnknown then return nil end;return w.builderPending==true end
o.settler.GetFormationUnitCount=function()return w.settlerFormation or 1 end
o.settler.IsDead=function()return w.settlerDead==true end
o.settler.IsDelayedDeath=function()return false end
o.settler.HasPendingOperations=function()return w.settlerPending==true end
UnitManager.GetActivityType=function(u)return u:GetID()==3 and(w.builderActivity or 1797587246)or 1797587246 end
local oldQueue=UnitManager.GetQueuedDestination
UnitManager.GetQueuedDestination=function(u)
 if u:GetID()==3 then if w.queueMany then return nil,nil end;return w.builderQueue end
 if u:GetID()==2 then return w.settlerQueue end
 return oldQueue(u)
end
local oldUnits=Units.GetUnitsInPlot
local other={GetID=function()return 55 end,GetOwner=function()return 7 end,GetUnitType=function()return 3 end}
Units.GetUnitsInPlot=function(p)
 local i=p:GetIndex()
 if i==274 then return{o.builder,o.army}end
 if i==230 then return{other,o.army}end
 if i==273 or i==317 then return w.parkBlocked and{other}or{o.army}end
 return oldUnits(p)
end
local oldPath=UnitManager.GetMoveToPathEx
UnitManager.GetMoveToPathEx=function(u,i)
 if u:GetID()==3 then
  w.pathQueries[#w.pathQueries+1]={unit=3,target=i}
  if(i==273 or i==317)and not w.noBuilderPath then return{plots={w.builderPlot,i}}end
  return{plots={}}
 end
 return oldPath(u,i)
end
local oldCan=UnitManager.CanStartOperation
UnitManager.CanStartOperation=function(u,op,mode,params)
 if u:GetID()==3 then
  if op==UnitOperationTypes.MOVE_TO then
   w.yieldChecks=w.yieldChecks+1;if w.onYieldCheck then w.onYieldCheck()end
   return true
  end
  if op==UnitOperationTypes.SKIP_TURN then return not(w.builderPending or w.builderQueue~=nil or w.queueMany)end
  if op==UnitOperationTypes.BUILD_IMPROVEMENT then return w.normalWork==true end
  return false
 end
 return oldCan(u,op,mode,params)
end
function InstallHeldSettler()
 local J=BaiqiSettlementJournal;local bank=J.New(7);bank.serial=1
 bank.operations['2']={unitID=2,unitType='UNIT_SETTLER',sequence=1,token=J.Token(7,1),
  turn=1,requestID='7:1:1',stage='ARMED',empty=true,conflictingCity=false,plot=845,x=9,y=19}
 assert(J.Validate(bank,7));w.settlementBank=bank;w.heldBefore=J.Clone(bank,7)
end
''')
        if change:lua.execute(change)
        return lua

    def run_one(self,lua):
        lua.globals().BaiqiController.RunNow()
        self.assertNotIn('脚本错误',lua.globals().BaiqiController.GetStatus())
        w=lua.globals().TestWorld
        self.assertTrue(all(r.unit in(2,3)for r in w.unitRequests.values()),'No army or held great person order')
        return[(r.params[14],r.params[15])for r in w.unitRequests.values()if r.unit==3 and r.op==10]

    def test_idle_builder_yields_only_its_own_qualified_step(self):
        for runtime in(Lua51,Lua53):
            with self.subTest(runtime=runtime.__module__):
                lua=self.world(runtime)
                self.assertEqual(self.run_one(lua),[(9,6)])
                self.assertEqual([(r.unit,r.op)for r in lua.globals().TestWorld.unitRequests.values()],[(3,10)])

    def test_ineligible_builder_or_settler_cannot_create_yield(self):
        cases={
            'queued':'TestWorld.builderQueue=0',
            'queue_unknown':'TestWorld.queueMany=true',
            'pending':'TestWorld.builderPending=true',
            'pending_unknown':'TestWorld.pendingUnknown=true',
            'escort':'TestWorld.builderFormation=2',
            'not_ready':'TestWorld.builderReady=false',
            'dead':'TestWorld.builderDead=true',
            'delayed':'TestWorld.builderDelayed=true',
            'settler_escort':'TestWorld.settlerFormation=2',
            'settler_pending':'TestWorld.settlerPending=true',
            'settler_queue':'TestWorld.settlerQueue=0',
            'settler_dead':'TestWorld.settlerDead=true',
            'goal_missing':"TestWorld.goalProposals['2']=nil",
            'held':'InstallHeldSettler()',
            'parking_occupied':'TestWorld.parkBlocked=true',
            'no_native_edge':'TestWorld.noBuilderPath=true',
        }
        for runtime in(Lua51,Lua53):
            for name,change in cases.items():
                with self.subTest(runtime=runtime.__module__,case=name):
                    lua=self.world(runtime,change)
                    self.assertEqual(self.run_one(lua),[])
                    if name=='held':lua.execute('assert(BaiqiSettlementJournal.Equal(TestWorld.heldBefore,TestWorld.settlementBank,7))')

    def test_actual_native_qualification_rechecks_yield_and_native_state(self):
        cases={
            'new_queue':'w.builderQueue=0',
            'new_pending':'w.builderPending=true',
            'new_escort':'w.builderFormation=2',
            'new_occupant':'w.parkBlocked=true',
            'goal_withdrawn':"w.goalProposals['2']=nil",
            'new_held':'InstallHeldSettler()',
        }
        for runtime in(Lua51,Lua53):
            for name,change in cases.items():
                with self.subTest(runtime=runtime.__module__,case=name):
                    lua=self.world(runtime,'local w=TestWorld;w.onYieldCheck=function()'+change+' end')
                    self.assertEqual(self.run_one(lua),[])
                    self.assertGreater(lua.globals().TestWorld.yieldChecks,0,'The actual native boundary must run')
                    if name=='new_held':lua.execute('assert(BaiqiSettlementJournal.Equal(TestWorld.heldBefore,TestWorld.settlementBank,7))')

    def test_ordinary_builder_work_keeps_priority(self):
        for runtime in(Lua51,Lua53):
            with self.subTest(runtime=runtime.__module__):
                lua=self.world(runtime,'''TestWorld.normalWork=true
TestWorld.plots[274].GetImprovementType=function()return-1 end''')
                self.assertEqual(self.run_one(lua),[])
                requests=list(lua.globals().TestWorld.unitRequests.values())
                self.assertEqual([(r.unit,r.op)for r in requests],[(3,lua.globals().UnitOperationTypes.BUILD_IMPROVEMENT)])

    def test_exhausted_route_wait_uses_yield_before_native_skip(self):
        for runtime in(Lua51,Lua53):
            with self.subTest(runtime=runtime.__module__):
                lua=self.world(runtime)
                lua.globals().BaiqiController.RunNow(False)
                self.assertEqual(lua.globals().TestBuilderRouteWait(),(True,False))
                requests=list(lua.globals().TestWorld.unitRequests.values())
                self.assertEqual([(r.unit,r.op,r.params[14],r.params[15])for r in requests],[(3,10,9,6)])

    def test_new_native_pending_is_not_cancelled_by_later_idle_wait(self):
        for runtime in(Lua51,Lua53):
            with self.subTest(runtime=runtime.__module__):
                lua=self.world(runtime,'TestWorld.onYieldCheck=function()TestWorld.builderPending=true end')
                self.assertEqual(self.run_one(lua),[])
                lua.globals().BaiqiController.RunNow()
                self.assertEqual([r for r in lua.globals().TestWorld.unitRequests.values()if r.unit==3],[])

    def test_second_settler_proposal_leaves_budget_for_final_recheck(self):
        for runtime in(Lua51,Lua53):
            with self.subTest(runtime=runtime.__module__):
                lua=self.world(runtime,'''local w,o=TestWorld,TestWorld.objects
local decoy=setmetatable({GetID=function()return 0 end},{__index=o.settler})
w.goalProposals['0']={unitID=0,unitType='UNIT_SETTLER',plot=845,x=9,y=19}
local oldUnits=o.player.GetUnits
o.player.GetUnits=function(self)
 local units=oldUnits(self);return{
  Members=function()local i=0;local list={o.army,decoy,o.settler,o.builder};return function()i=i+1;if list[i]then return i,list[i]end end end,
  FindID=function(_,id)if id==0 then return decoy end;return units:FindID(id)end}
end
local oldPath=UnitManager.GetMoveToPathEx
UnitManager.GetMoveToPathEx=function(u,index)
 if u:GetID()==0 then w.decoyPaths=(w.decoyPaths or 0)+1;return{plots={229,845}}end
 return oldPath(u,index)
end''')
                lua.globals().BaiqiController.RunNow(False)
                self.assertEqual(lua.globals().TestBuilderRouteWait(),(True,False))
                w=lua.globals().TestWorld
                self.assertEqual(w.decoyPaths,1)
                self.assertEqual([(r.unit,r.op,r.params[14],r.params[15])for r in w.unitRequests.values()],[(3,10,9,6)])


if __name__=='__main__':unittest.main()
