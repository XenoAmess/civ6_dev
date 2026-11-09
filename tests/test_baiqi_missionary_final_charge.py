"""Real Core event/receipt consumer; deleted actors alone never prove spread."""
from pathlib import Path
import os
import unittest
from lupa.lua51 import LuaRuntime

ROOT=Path(__file__).resolve().parents[1]
FIXTURE=r'''
W={turn=139,owner=0,unitID=0,cityID=65536,cityOwner=0,x=-9999,y=-9999,dead=true,
 charges=0,religion=1,created=1,formation=1,moves=4,unitType=60,writes=0,allowWrite=true,
 unitReads=0,callbacks={},removed={},playerID=0}
function Copy(v)if type(v)~='table'then return v end;local r={};for k,x in pairs(v)do r[k]=Copy(x)end;return r end
local u={GetID=function()return W.unitID end,GetOwner=function()return W.owner end,
 GetType=function()return W.unitType end,GetX=function()
  W.unitReads=W.unitReads+1;if W.changeReadAt==W.unitReads then W.formation=2 end;return W.x end,
 GetY=function()return W.y end,IsDelayedDeath=function()return W.dead end,
 GetMovesRemaining=function()return W.moves end,GetFormationUnitCount=function()return W.formation end,
 GetReligion=function()return {GetReligionType=function()return W.religion end,GetSpreadCharges=function()return W.charges end}end}
local city={GetID=function()return W.cityID end,GetOwner=function()return W.cityOwner end,
 GetX=function()return 55 end,GetY=function()return 34 end}
local player={IsHuman=function()return not W.ai end,IsTurnActive=function()return true end,
 GetProperty=function(_,key)
  assert(key=='BAIQI_RELIGIOUS_INTENTS_V1')
  if W.propertyHook then local f=W.propertyHook;W.propertyHook=nil;f()end
  return Copy(W.store) end,
 SetProperty=function(_,key,value)
  assert(key=='BAIQI_RELIGIOUS_INTENTS_V1');W.writes=W.writes+1
  if W.writeThrow then error('write')end
  if W.allowWrite then W.store=Copy(value)end end,
 GetReligion=function()return {GetReligionTypeCreated=function()return W.created end}end,
 GetCities=function()return {FindID=function(_,id)if not W.noCity and id==65536 then return city end end}end,
 GetUnits=function()return {
  FindID=function(_,id)if not W.missing and id==0 then return u end end,
  Members=function()return function()end end}end}
Players={[0]=player};PlayerConfigurations={[0]={GetLeaderTypeName=function()return W.foreignLeader and 'OTHER'or'LEADER_BAIQI'end}}
Game={GetLocalPlayer=function()return W.playerID end,GetCurrentGameTurn=function()return W.turn end}
GameConfiguration={IsAnyMultiplayer=function()return W.multiplayer==true end,IsHotseat=function()return false end}
GameInfo={Units={[60]={UnitType='UNIT_MISSIONARY'},[61]={UnitType='UNIT_APOSTLE'}},
 UnitOperations={UNITOPERATION_SPREAD_RELIGION={Hash=1592408602}}}
BaiqiConfig={leader='LEADER_BAIQI',religiousIntentKey='BAIQI_RELIGIOUS_INTENTS_V1'}
ExposedMembers={};GameEvents={};Events={}
for _,eventName in ipairs({'UnitOperationStarted','UnitChargesChanged','UnitRemovedFromMap','UnitOperationDeactivated'})do
 local name=eventName;W.callbacks[name]={};W.removed[name]=0
 Events[name]={Add=function(...)
  assert(select('#',...)==1);local cb=...;table.insert(W.callbacks[name],cb)
  if W.failAdd==name then error('after attach')end
 end,Remove=function(...)
  assert(select('#',...)==1);local cb=...;W.removed[name]=W.removed[name]+1
  if W.failRemove==name then return false end
  for i,f in ipairs(W.callbacks[name])do if f==cb then table.remove(W.callbacks[name],i);return end end
  error('duplicate or foreign removal')
 end}
end
function Emit(name,...)
 local list={};for i,fn in ipairs(W.callbacks[name])do list[i]=fn end
 for _,fn in ipairs(list)do fn(...)end
end
function Pair()Emit('UnitOperationStarted',0,0,1592408602,0);Emit('UnitChargesChanged',0,0,0,1)end
function include()end
print=function()end
'''

class FinalChargeCoreTests(unittest.TestCase):
    def setUp(self):
        self.lua=LuaRuntime(unpack_returned_tuples=True);self.lua.execute(FIXTURE)
        self.lua.execute((ROOT/'mod/Baiqi/Lua/BaiqiPolicy.lua').read_text(encoding='utf-8'))
        self.lua.execute((ROOT/'mod/Baiqi/Lua/BaiqiReligiousJournal.lua').read_text(encoding='utf-8'))
        self.lua.execute("""W.store={version=1,owner=0,serial=1,operations={['0']={
         token='religion:0:1',sequence=1,unitID=0,unitType='UNIT_MISSIONARY',religion=1,charges=1,
         x=55,y=34,cityID=65536,cityX=55,cityY=34,turn=139,stage='ARMED'}}}""")
        self.w=self.lua.globals().W

    def load(self,change=''):
        if change:self.lua.execute(change)
        source=Path(os.environ.get('BAIQI_FINAL_RECEIPT_SOURCE')or ROOT/'mod/Baiqi/Lua/BaiqiReligiousIntentGameplay.lua')
        self.lua.execute(source.read_text(encoding='utf-8'))
        self.module=self.lua.globals().BaiqiReligiousIntentGameplay
        self.bridge=self.lua.globals().ExposedMembers.BaiqiReligiousIntentBridge

    def pair(self):self.lua.globals().Pair()

    def stage(self):return self.w.store.operations['0'].stage

    def test_native_shaped_postdeath_pair_confirms_only_original_record(self):
        self.load();self.pair()
        self.assertEqual((self.stage(),self.w.writes),('OBSERVED',1))
        self.assertEqual((self.w.store.serial,self.w.store.operations['0'].charges,self.w.store.operations['0'].token),
                         (1,1,'religion:0:1'))
        self.pair();self.assertEqual(self.w.writes,1)

    def test_disappearance_or_one_event_or_wrong_order_does_not_confirm(self):
        for events in ("", "Emit('UnitRemovedFromMap',0,0)","Emit('UnitChargesChanged',0,0,0,1)",
                       "Emit('UnitOperationStarted',0,0,1592408602,0)",
                       "Emit('UnitChargesChanged',0,0,0,1);Emit('UnitOperationStarted',0,0,1592408602,0)"):
            with self.subTest(events=events):
                self.setUp();self.load();self.lua.execute(events)
                self.assertEqual((self.stage(),self.w.writes),('ARMED',0))

    def test_wrong_actor_event_delta_hash_and_intervening_end_are_denied(self):
        changes=("Emit('UnitOperationStarted',1,0,1592408602,0);Emit('UnitChargesChanged',0,0,0,1)",
                 "Emit('UnitOperationStarted',0,1,1592408602,0);Emit('UnitChargesChanged',0,0,0,1)",
                 "Emit('UnitOperationStarted',0,0,10,0);Emit('UnitChargesChanged',0,0,0,1)",
                 "Emit('UnitOperationStarted',0,0,1592408602,0);Emit('UnitChargesChanged',0,0,0,2)",
                 "Emit('UnitOperationStarted',0,0,1592408602,0);Emit('UnitOperationDeactivated',0,0,1592408602,1);Emit('UnitChargesChanged',0,0,0,1)")
        for change in changes:
            with self.subTest(change=change):
                self.setUp();self.load();self.lua.execute(change)
                self.assertEqual((self.stage(),self.w.writes),('ARMED',0))

    def test_actual_owner_type_religion_city_formation_and_context_required(self):
        changes=("W.owner=1","W.unitID=99","W.missing=true","W.noCity=true","W.cityID=99","W.cityOwner=1",
                 "W.religion=2","W.created=2","W.formation=2","W.unitType=61","W.turn=140",
                 "W.dead=false","W.x=55","W.ai=true","W.multiplayer=true","W.foreignLeader=true")
        for change in changes:
            with self.subTest(change=change):
                self.setUp();self.load();self.lua.execute(change);self.pair()
                self.assertEqual((self.stage(),self.w.writes),('ARMED',0))

    def test_changed_journal_or_foreign_bridge_after_start_is_not_overwritten(self):
        for change in ("W.store.serial=2;W.store.operations['0'].sequence=2;W.store.operations['0'].token='religion:0:2'",
                       "W.store.operations['0'].cityID=9","W.store.extra=true","ExposedMembers.BaiqiReligiousIntentBridge={}"):
            with self.subTest(change=change):
                self.setUp();self.load();self.lua.execute("Emit('UnitOperationStarted',0,0,1592408602,0);"+change+";Emit('UnitChargesChanged',0,0,0,1)")
                self.assertEqual(self.w.writes,0)

    def test_actor_change_during_repeat_reads_stays_unknown(self):
        self.load();self.lua.execute("Emit('UnitOperationStarted',0,0,1592408602,0)")
        self.w.changeReadAt=self.w.unitReads+1
        self.lua.execute("Emit('UnitChargesChanged',0,0,0,1)")
        self.assertEqual((self.stage(),self.w.writes),('ARMED',0))

    def test_missing_namespace_is_not_initialized_by_events(self):
        self.load();self.w.store=None;self.pair()
        self.assertIsNone(self.w.store);self.assertEqual(self.w.writes,0)

    def test_saved_armed_without_new_events_and_failed_writes_remain_armed(self):
        self.load()
        self.assertEqual(self.bridge.Inspect(0,0)[0],'ARMED')
        self.assertEqual(self.w.writes,0)
        for change in ('W.allowWrite=false','W.writeThrow=true'):
            with self.subTest(change=change):
                self.setUp();self.load();self.lua.execute(change);self.pair()
                self.assertEqual(self.stage(),'ARMED')

    def test_shutdown_removes_exact_callbacks_and_retries_only_failures(self):
        self.load();self.w.failRemove='UnitChargesChanged'
        self.assertFalse(self.module.Shutdown());self.pair()
        self.assertEqual(self.w.writes,0)
        self.w.failRemove=None;self.assertTrue(self.module.Shutdown());self.assertTrue(self.module.Shutdown())
        self.assertEqual(self.w.removed['UnitChargesChanged'],2)
        self.assertEqual(self.w.removed['UnitOperationStarted'],1)

    def test_add_failure_cleans_current_attachment_and_disables_partial_observation(self):
        self.load("W.failAdd='UnitChargesChanged'")
        self.assertTrue(self.lua.eval("(function()for _,list in pairs(W.callbacks)do if #list~=0 then return false end end;return true end)()"))
        self.pair();self.assertEqual((self.stage(),self.w.writes),('ARMED',0))

    def test_private_static_control_does_not_subscribe_or_observe_final_events(self):
        from tools.static_control_source import transform
        text=(ROOT/'mod/Baiqi/Lua/BaiqiReligiousIntentGameplay.lua').read_text(encoding='utf-8')
        controlled,_=transform(text,'Lua/BaiqiReligiousIntentGameplay.lua',105)
        self.lua.execute(controlled);self.pair()
        self.assertEqual((self.stage(),self.w.writes),('ARMED',0))
        self.assertTrue(self.lua.eval("(function()for _,list in pairs(W.callbacks)do if #list~=0 then return false end end;return true end)()"))

if __name__=='__main__':unittest.main()
