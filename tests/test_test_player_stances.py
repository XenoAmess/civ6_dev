"""Pure Lua consumers of the test player's distinct stance tool; no live SDK."""
from pathlib import Path
import unittest
from lupa.lua51 import LuaRuntime as Lua51
from lupa.lua53 import LuaRuntime as Lua53

ROOT=Path(__file__).resolve().parents[1]
SOURCE=(ROOT/'tools/lua/test_player_stances.lua').read_text(encoding='utf-8')
FIXTURE=r'''
function setup(mode)
 calls={};busy=false;selected=nil;units={};local ready={};local queued={}
 local defs={{UnitType='UNIT_WARRIOR',Combat=20},{UnitType='UNIT_BUILDER',Combat=0},
  {UnitType='UNIT_APOSTLE',Combat=0},{UnitType='UNIT_SCOUT',Combat=10},
  {UnitType='UNIT_GREAT_ADMIRAL',Combat=0},{UnitType='UNIT_MISSIONARY',Combat=0}}
 for i=1,6 do local u={id=i,kind=i};ready[i]=true
  function u:GetID()return self.id end
  function u:GetOwner()return mode=='foreign'and self.id==1 and 1 or 0 end
  function u:GetUnitType()return self.kind end
  function u:IsDead()return mode=='dead'and self.id==1 end
  function u:IsDelayedDeath()return mode=='delayed'and self.id==1 end
  function u:GetFormationUnitCount()return mode=='escort'and self.id==1 and 2 or 1 end
  function u:GetMovesRemaining()return mode=='zero'and self.id==1 and 0 or 2 end
  function u:IsReadyToMove()return ready[self.id]end
  function u:IsReadyToSelect()return ready[self.id]end
  function u:HasPendingOperations()return mode=='pending'and self.id==1 end
  function u:GetX()return self.id end
  function u:GetY()return 0 end
  units[i]=u
 end
 local all={Members=function()return ipairs(units)end,FindID=function(_,id)return units[id]end}
 Players={[0]={GetUnits=function()return all end,IsTurnActive=function()return mode~='inactive'end}}
 PlayerConfigurations={[0]={IsHuman=function()return mode~='nonhuman'end,GetLeaderTypeName=function()return mode=='qin'and'LEADER_QIN'or'LEADER_BAIQI'end}}
 Game={GetCurrentGameTurn=function()return 132 end,GetLocalPlayer=function()return 0 end,IsAllowStrategicCommands=function()return true end}
 GameConfiguration={IsAnyMultiplayer=function()return mode=='mp'end,IsHotseat=function()return mode=='hotseat'end}
 GameInfo={Units=defs,UnitOperations={UNITOPERATION_SKIP_TURN={Hash=77},UNITOPERATION_FORTIFY={Hash=88},UNITOPERATION_SLEEP={Hash=99}}}
 UI={IsGameCoreBusy=function()return busy end,IsProcessingMessages=function()return false end,HasSentTurnComplete=function()return false end,
  SelectUnit=function(u)selected=u end,GetHeadSelectedUnit=function()return selected end}
 UnitManager={GetQueuedDestination=function(u)if queued[u.id]or(mode=='queued'and u.id==1)then return 100 end end,
  CanStartOperation=function(u,action,unused,params)
   assert(unused==nil and type(params)=='table'and next(params)==nil)
   if mode=='driftAction'and u.id==1 then GameInfo.UnitOperations.UNITOPERATION_FORTIFY.Hash=777 end
   if mode=='driftType'and u.id==1 then u.kind=2 end
   if mode=='driftQueue'and u.id==1 then queued[1]=true end
   if mode=='reject'and u.id==1 then return false end
   return(action==88 and(u.id==1 or u.id==4))or(action==99 and(u.id==3 or u.id==5))
  end,
  RequestOperation=function(u,action,params)
   assert(u.id~=2 and u.id~=6 and(action==88 or action==99)and type(params)=='table'and next(params)==nil)
   calls[#calls+1]={id=u.id,action=action}
   if mode=='busy'then busy=true end
   if mode=='throw'then error('unknown native result')end
   if mode=='false'then return false end
   ready[u.id]=false
  end}
 return{attempts={}}
end
'''


class TestPlayerStances(unittest.TestCase):
    def fixture(self,vm,mode='normal'):
        lua=vm(unpack_returned_tuples=True);lua.execute(FIXTURE)
        run=lua.execute(SOURCE);state=lua.globals().setup(mode)
        return lua,run,state

    def ids(self,lua):
        return [row.id for row in lua.globals().calls.values()]

    def test_two_distinct_stances_never_target_civilians_or_repeat_same_unit(self):
        for vm in [Lua51,Lua53]:
            lua,run,state=self.fixture(vm)
            self.assertEqual(run(132,64,state,88).submitted,2)
            self.assertEqual(run(132,64,state,99).submitted,2)
            self.assertEqual(self.ids(lua),[1,4,3,5])
            self.assertEqual(run(132,64,state,88).submitted,0)
            self.assertEqual(run(132,64,state,99).submitted,0)
            self.assertEqual(len(lua.globals().calls),4)

    def test_ineligible_actor_and_reentrant_changes_never_reach_writer(self):
        modes=['foreign','dead','delayed','escort','zero','pending','queued','reject','driftType','driftQueue']
        for vm in [Lua51,Lua53]:
            for mode in modes:
                with self.subTest(vm=vm.__module__,mode=mode):
                    lua,run,state=self.fixture(vm,mode);run(132,64,state,88)
                    self.assertEqual(self.ids(lua),[4]);self.assertIsNone(state.attempts[1])

    def test_phase_and_action_argument_failures_have_zero_native_calls(self):
        for vm in [Lua51,Lua53]:
            for mode in ['qin','nonhuman','mp','hotseat','inactive']:
                with self.subTest(vm=vm.__module__,mode=mode):
                    lua,run,state=self.fixture(vm,mode)
                    with self.assertRaises(Exception):run(132,64,state,88)
                    self.assertEqual(self.ids(lua),[])
            for action in [77,100,True,None]:
                lua,run,state=self.fixture(vm)
                with self.assertRaises(Exception):run(132,64,state,action)
                self.assertEqual(self.ids(lua),[])
            lua,run,state=self.fixture(vm,'driftAction');run(132,64,state,88)
            self.assertEqual(self.ids(lua),[])

    def test_false_and_throwing_outcomes_are_consumed_before_any_second_action(self):
        for vm in [Lua51,Lua53]:
            for mode in ['false','throw']:
                with self.subTest(vm=vm.__module__,mode=mode):
                    lua,run,state=self.fixture(vm,mode);report=run(132,64,state,88)
                    self.assertEqual(state.attempts[1].effect,'UNKNOWN')
                    self.assertEqual(state.attempts[1].nativeReturned,mode!='throw')
                    self.assertEqual(report.nativeError,mode=='throw')
                    run(132,64,state,99)
                    self.assertEqual(self.ids(lua).count(1),1)

    def test_limit_duplicate_and_midloop_busy_preserve_independent_attempts(self):
        for vm in [Lua51,Lua53]:
            lua,run,state=self.fixture(vm);state.attempts[1]=lua.table(id=1)
            self.assertEqual(run(132,1,state,88).submitted,1);self.assertEqual(self.ids(lua),[4])
            lua,run,state=self.fixture(vm,'busy');report=run(132,64,state,88)
            self.assertEqual(self.ids(lua),[1]);self.assertTrue(report.phaseStopped)


if __name__=='__main__':unittest.main()
