"""Actual proposal storage, including identity and mutation callbacks; no game orders."""
from pathlib import Path
import unittest
from lupa.lua51 import LuaRuntime

ROOT=Path(__file__).resolve().parents[1]

WORLD=r'''
W={turn=10,active=true,human=true,leader='LEADER_BAIQI',localID=0,width=10,height=10,writes=0,reads=0,units={},revealed=true}
local function Add(id)
 local u={};u.GetID=function()return id end;u.GetOwner=function()return W.foreignActor and 8 or 0 end
 u.GetType=function()return 1 end;u.GetX=function()return 1 end;u.GetY=function()return 1 end
 u.IsDead=function()return false end;u.IsDelayedDeath=function()return false end
 u.GetMovesRemaining=function()return W.moves or 2 end;u.GetFormationUnitCount=function()return W.formation or 1 end
 W.units[id]=u;return u
end
W.Add=Add;Add(393216)
local p={}
function p:IsTurnActive()return W.active end
function p:GetProperty(key)
 assert(key=='GOALS','Read touched founding journal or another property');W.reads=W.reads+1
 if W.getHook then W.getHook(W.reads)end
 return W.bank
end
function p:SetProperty(key,value)
 assert(key=='GOALS','Write touched founding journal or another property');W.writes=W.writes+1
 if W.setHook then return W.setHook(value)end
 W.bank=value
end
function p:GetUnits()
 return {Members=function()return pairs(W.units)end,FindID=function(_,id)
   if W.alias and id==393216 then return W.units[2]end
   if W.staleAlias and id==2 then return W.units[393216]end
   return W.units[id]
 end}
end
local visibility={IsRevealed=function(_,x,y)return W.revealed end}
E={Game={GetLocalPlayer=function()return W.localID end,GetCurrentGameTurn=function()return W.turn end,
 IsAllowStrategicCommands=function()return W.strategic~=false end},
 GameConfiguration={IsAnyMultiplayer=function()return W.multiplayer==true end,IsHotseat=function()return W.hotseat==true end},
 Players={[0]=p},PlayerConfigurations={[0]={IsHuman=function()return W.human end,GetLeaderTypeName=function()return W.leader end}},
 GameInfo={Units={[1]={UnitType='UNIT_SETTLER'}}},PlayersVisibility={[0]=visibility},
 Map={GetGridSize=function()return W.width,W.height end,GetPlotByIndex=function(index)
  return {GetIndex=function()return index end,GetX=function()return index%W.width end,
   GetY=function()return math.floor(index/W.width)end}
 end}}
C={leader='LEADER_BAIQI',settlerGoalsKey='GOALS',settlementIntentKey='FOUND'}
API=assert(BaiqiSettlerGoalsCore.Create(C,BaiqiSettlerGoals,BaiqiSettlementJournal,BaiqiSettlementUnitCore,E))
function Remember()return API.Remember(0,393216,21,1,2)end
function Goal(id,plot)return {unitID=id,unitType='UNIT_SETTLER',plot=plot,x=plot%10,y=math.floor(plot/10)}end
'''


class SettlerGoalsCoreTests(unittest.TestCase):
    def setUp(self):
        self.lua=LuaRuntime(unpack_returned_tuples=True)
        for name in ('BaiqiSettlerGoals','BaiqiSettlementJournal','BaiqiSettlementUnitCore','BaiqiSettlerGoalsCore'):
            self.lua.execute((ROOT/'mod/Baiqi/Lua'/f'{name}.lua').read_text(encoding='utf-8'))
        self.lua.execute(WORLD)
        self.w=self.lua.globals().W

    def test_actual_per_player_visibility_shape_creates_service(self):
        self.assertIsNone(self.lua.globals().E.PlayersVisibility.IsRevealed)
        self.assertEqual(self.lua.eval('Remember()')[0],'READY')
        self.assertEqual(self.w.writes,1)
        self.assertEqual(self.w.bank.goals['393216'].plot,21)

    def test_empty_read_is_proposal_without_property_write(self):
        self.assertEqual(self.lua.eval('API.Read(0,393216)')[:2],('READY',None))
        self.assertEqual(self.w.writes,0)
        self.assertIsNone(self.w.bank)

    def test_remember_is_idempotent_and_supports_new_target(self):
        self.assertEqual(self.lua.eval('Remember()')[0],'READY')
        self.assertEqual(self.lua.eval('Remember()')[0],'READY')
        self.assertEqual(self.w.writes,1)
        self.assertEqual(self.lua.eval('API.Remember(0,393216,23,3,2)')[0],'READY')
        self.assertEqual((self.w.writes,self.w.bank.goals['393216'].plot),(2,23))

    def test_read_returns_detached_proposal(self):
        self.lua.execute("Remember();local s,g=API.Read(0,393216);assert(s=='READY');g.plot=99")
        self.assertEqual(self.w.bank.goals['393216'].plot,21)

    def test_forget_works_after_unit_absence_and_is_idempotent(self):
        self.lua.execute('Remember();W.units[393216]=nil')
        self.assertEqual(self.lua.eval('API.Forget(0,393216)')[0],'READY')
        self.assertEqual(self.lua.eval('API.Forget(0,393216)')[0],'READY')
        self.assertEqual(self.w.writes,2)

    def test_escort_alias_capture_and_zero_moves_cannot_remember(self):
        for change in ('W.formation=2','W.moves=0','W.foreignActor=true','W.Add(2);W.alias=true'):
            with self.subTest(change=change):
                self.setUp();self.lua.execute(change)
                self.assertEqual(self.lua.eval('Remember()')[0],'UNAVAILABLE')
                self.assertEqual(self.w.writes,0)

    def test_owner_turn_multiplayer_and_strategic_gates(self):
        for change in ('W.active=false','W.localID=1','W.human=false',"W.leader='OTHER'",'W.multiplayer=true','W.hotseat=true','W.strategic=false'):
            with self.subTest(change=change):
                self.setUp();self.lua.execute(change)
                self.assertEqual(self.lua.eval('Remember()')[0],'UNAVAILABLE')
                self.assertEqual(self.w.writes,0)

    def test_invalid_index_and_hidden_site_never_write(self):
        self.assertEqual(self.lua.eval('API.Remember(0,393216,22,1,2)')[0],'UNAVAILABLE')
        self.w.revealed=False
        self.assertEqual(self.lua.eval('Remember()')[0],'UNAVAILABLE')
        self.assertEqual(self.w.writes,0)

    def test_malformed_existing_state_is_preserved(self):
        self.lua.execute('W.bank={version=99}')
        self.assertEqual(self.lua.eval('API.Read(0,393216)')[0],'UNAVAILABLE')
        self.assertEqual(self.lua.eval('Remember()')[0],'UNAVAILABLE')
        self.assertEqual(self.w.bank.version,99)
        self.assertEqual(self.w.writes,0)

    def test_foreign_reservation_is_not_overwritten(self):
        self.lua.execute("W.Add(2);W.bank=BaiqiSettlerGoals.New(0,10,10);W.bank.goals['2']=Goal(2,21)")
        self.assertEqual(self.lua.eval('Remember()')[0],'UNAVAILABLE')
        self.assertEqual(self.w.writes,0)

    def test_stale_absent_or_alias_proposal_retirement_does_not_touch_found(self):
        for change in ('', 'W.staleAlias=true'):
            with self.subTest(change=change):
                self.setUp();self.lua.execute("W.bank=BaiqiSettlerGoals.New(0,10,10);W.bank.goals['2']=Goal(2,21);"+change)
                self.assertEqual(self.lua.eval('Remember()')[0],'READY')
                self.assertIsNone(self.w.bank.goals['2'])
                self.assertEqual(self.w.bank.goals['393216'].plot,21)

    def test_capacity_counts_current_live_actors(self):
        self.lua.execute("W.bank=BaiqiSettlerGoals.New(0,10,10);for i=1,32 do W.Add(i);W.bank.goals[tostring(i)]=Goal(i,i-1)end")
        self.assertEqual(self.lua.eval('API.Remember(0,393216,99,9,9)')[0],'UNAVAILABLE')
        self.assertEqual(self.w.writes,0)

    def test_owner_map_turn_or_moves_changed_during_read_blocks_write(self):
        for change in ('W.active=false','W.width=11','W.turn=11','W.moves=0'):
            with self.subTest(change=change):
                self.setUp();self.lua.execute('W.getHook=function(n)if n==2 then '+change+' end end')
                self.assertEqual(self.lua.eval('Remember()')[0],'UNAVAILABLE')
                self.assertEqual(self.w.writes,0)

    def test_concurrent_bank_change_is_preserved(self):
        self.lua.execute("W.getHook=function(n)if n==2 then W.bank=BaiqiSettlerGoals.New(0,10,10);W.bank.goals['2']=Goal(2,31)end end")
        self.assertEqual(self.lua.eval('Remember()')[0],'UNAVAILABLE')
        self.assertEqual(self.w.bank.goals['2'].plot,31)
        self.assertEqual(self.w.writes,0)

    def test_valid_but_wrong_writeback_is_not_acknowledged(self):
        self.lua.execute('W.setHook=function(v)W.bank=BaiqiSettlerGoals.New(0,10,10)end')
        self.assertEqual(self.lua.eval('Remember()')[0],'UNAVAILABLE')
        self.assertEqual(self.w.writes,1)

    def test_apply_then_throw_is_observed_without_second_write(self):
        self.lua.execute("W.setHook=function(v)W.bank=v;error('AFTER_APPLY')end")
        self.assertEqual(self.lua.eval('Remember()')[0],'UNAVAILABLE')
        self.w.setHook=None
        self.assertEqual(self.lua.eval('Remember()')[0],'READY')
        self.assertEqual(self.w.writes,1)

    def test_getter_error_is_unavailable_not_empty(self):
        self.lua.execute("W.getHook=function()error('GET_FAILED')end")
        self.assertEqual(self.lua.eval('API.Read(0,393216)')[0],'UNAVAILABLE')
        self.assertEqual(self.w.writes,0)

    def test_reentrant_mutation_is_rejected(self):
        self.lua.execute("W.getHook=function(n)if n==1 then W.inner=API.Forget(0,393216)end end")
        self.assertEqual(self.lua.eval('Remember()')[0],'READY')
        self.assertEqual(self.w.inner,'UNAVAILABLE')
        self.assertEqual(self.w.writes,1)

    def test_snapshot_map_change_is_unavailable(self):
        self.lua.execute('W.getHook=function()W.width=11 end')
        self.assertEqual(self.lua.eval('API.Read(0,393216)')[0],'UNAVAILABLE')
        self.assertEqual(self.w.writes,0)


if __name__=='__main__':unittest.main()
