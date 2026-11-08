"""Execute actual recursively included Core sources, not fake bridge bodies."""
from pathlib import Path
import unittest
from lupa.lua53 import LuaRuntime
from tools.static_control_source import transform

ROOT=Path(__file__).resolve().parents[1]


class CoreHarness:
    def __init__(self,control=True):
        self.lua=LuaRuntime(unpack_returned_tuples=True);self.seen=set();self.control=control
        self.lua.execute('''
T={reads=0,playerWrites=0,plotWrites=0,gameWrites=0,benefits=0,store={},props={BAIQI_RIGHTS_V1={old=true}}}
local function event()
 local callbacks={};return {Add=function(fn) assert(type(fn)=='function');callbacks[#callbacks+1]=fn end,
 Remove=function(fn) for i=#callbacks,1,-1 do if callbacks[i]==fn then table.remove(callbacks,i) end end end,
 Fire=function(...) for _,fn in ipairs(callbacks) do fn(...) end end,Count=function() return #callbacks end}
end
local function events() return setmetatable({},{__index=function(t,k) local e=event();rawset(t,k,e);return e end}) end
Events=events();GameEvents=events();ExposedMembers={}
Game={GetLocalPlayer=function() T.reads=T.reads+1;return 7 end,GetCurrentGameTurn=function() return 85 end,
 GetProperty=function(k) return T.props[k] end,SetProperty=function(k,v) T.gameWrites=T.gameWrites+1;T.props[k]=v end}
GameConfiguration={IsAnyMultiplayer=function() return false end,IsHotseat=function() return false end}
local player={IsHuman=function() return true end,IsTurnActive=function() return true end,
 GetProperty=function(_,k) return T.store[k] end,SetProperty=function(_,k,v) T.playerWrites=T.playerWrites+1;T.store[k]=v end,
 GetUnits=function() return {Members=function() return function() end end,FindID=function() end} end}
Players={[7]=player};PlayerConfigurations={[7]={GetLeaderTypeName=function() return 'LEADER_BAIQI' end}}
PlayerManager={GetAliveIDs=function() return {7} end}
T.store.BAIQI_STATE_V1={old=true}
function player:GetTreasury() return {ChangeGoldBalance=function() T.benefits=T.benefits+1 end} end
T.plots={}
for i=0,1 do local p={values={BAIQI_GRANARY_IN=9,BAIQI_GRANARY_OUT=7}}
 function p:SetProperty(k,v) T.plotWrites=T.plotWrites+1;self.values[k]=v end;T.plots[i]=p end
Map={GetPlotCount=function() return 2 end,GetPlotByIndex=function(i) return T.plots[i] end}
local function forbidden() T.benefits=T.benefits+1 end
GameInfo={};UnitManager={RequestOperation=forbidden,RequestCommand=forbidden};CityManager={RequestOperation=forbidden,RequestCommand=forbidden};PlayersVisibility={}
print=function() end
include=function(name) return LoadActual(name) end
''')
        self.lua.globals().LoadActual=self.load

    def load(self,name):
        if name in self.seen:return
        self.seen.add(name)
        key=f'Lua/{name}.lua';source=(ROOT/'mod/Baiqi'/key).read_text(encoding='utf-8')
        if self.control:source=transform(source,key)[0]
        return self.lua.execute(source)


class StaticControlCoreTests(unittest.TestCase):
    def test_actual_seven_bridges_reject_without_domain_reads_or_writes(self):
        h=CoreHarness();h.load('BaiqiGameplay');g=h.lua.globals();t=g.T
        names=('BaiqiGreatPersonIntentBridge','BaiqiCreativeIntentBridge','BaiqiReligiousIntentBridge',
               'BaiqiNaturalistIntentBridge','BaiqiNaturalistPurchaseBridge','BaiqiArchaeologyBridge',
               'BaiqiMissionaryPurchaseBridge')
        for name in names:
            bridge=g.ExposedMembers[name];self.assertIsNotNone(bridge,name)
            self.assertEqual(bridge.Inspect(7,4),('UNAVAILABLE',None,'private_static_control'),name)
            methods=('PrepareExcavation','PrepareChoice','PreparePendingChoice') if name=='BaiqiArchaeologyBridge' else ('Prepare',)
            for method in methods:self.assertEqual(bridge[method](7,4),(False,None,'private_static_control'),(name,method))
        self.assertEqual(g.ExposedMembers.BaiqiGreatPersonIntentBridge.Observe(7,4)[0],'UNAVAILABLE')
        self.assertFalse(g.BaiqiArchaeologyIntentGameplay.ObserveCreated(7,4))
        self.assertEqual(g.BaiqiReligiousIntentGameplay.Initialize(7),(False,None,'private_static_control'))
        self.assertEqual((t.reads,t.playerWrites,t.plotWrites,t.gameWrites),(0,0,0,0))
        self.assertTrue({'BaiqiGPJournal','BaiqiCreativeJournal','BaiqiReligiousJournal','BaiqiArchaeologyJournal'}.issubset(h.seen))

    def test_actual_captured_receipt_and_unit_callbacks_cannot_write_journals(self):
        h=CoreHarness();h.load('BaiqiGameplay');g=h.lua.globals();t=g.T
        for name in ('GreatWorkCreated','UnitAddedToMap','PlayerTurnDeactivated'):
            event=g.Events[name];self.assertGreater(event.Count(),0,name)
            event.Fire(7,4,3,3,100,12)
        self.assertEqual((t.reads,t.playerWrites,t.plotWrites,t.gameWrites),(0,0,0,0))
        self.assertGreater(g.GameEvents.OnGameTurnStarted.Count(),1)
        # A real untransformed bootstrap exercises the same fixture's domain path.
        normal=CoreHarness(control=False)
        for name in ('BaiqiConfig','BaiqiPolicy','BaiqiRequisition','BaiqiGPIntentGameplay'):normal.load(name)
        self.assertGreater(normal.lua.globals().T.reads,0)
        self.assertGreater(normal.lua.globals().T.playerWrites,0)

    def test_original_withdrawn_cleanup_runs_once_without_benefits(self):
        h=CoreHarness();h.load('BaiqiGameplay');g=h.lua.globals();t=g.T
        event=g.GameEvents.OnGameTurnStarted;event.Fire()
        self.assertEqual((t.plotWrites,t.gameWrites,t.playerWrites,t.benefits),(4,2,1,0))
        self.assertIsNone(t.store.BAIQI_STATE_V1)
        self.assertIsNone(t.props.BAIQI_RIGHTS_V1);self.assertEqual(t.props.BAIQI_WITHDRAWN_RIGHTS_CLEANED,2)
        for i in (0,1):
            self.assertEqual(t.plots[i]['values'].BAIQI_GRANARY_IN,0)
            self.assertEqual(t.plots[i]['values'].BAIQI_GRANARY_OUT,0)
        event.Fire();self.assertEqual((t.plotWrites,t.gameWrites,t.playerWrites,t.reads,t.benefits),(4,2,1,0,0))

    def test_owned_event_unsubscribe_keeps_foreign_callbacks(self):
        h=CoreHarness();h.load('BaiqiGameplay');g=h.lua.globals()
        h.lua.execute("T.foreign=0;Events.GreatWorkCreated.Add(function() T.foreign=T.foreign+1 end)")
        before=g.Events.GreatWorkCreated.Count()
        g.BaiqiArchaeologyReceiptEvents.Shutdown()
        self.assertEqual(g.Events.GreatWorkCreated.Count(),before-1)
        g.Events.GreatWorkCreated.Fire(7,4,3,3,100,12)
        self.assertEqual((g.T.foreign,g.T.playerWrites),(1,0))


    def test_actual_prophet_bridge_static_control(self):
        h=CoreHarness();h.load('BaiqiGameplay');g=h.lua.globals();t=g.T
        bridge=g.ExposedMembers.BaiqiProphetIntentBridge
        self.assertIsNotNone(bridge)
        self.assertEqual(bridge.version,1)
        self.assertEqual(bridge.marker,'baiqi-prophet-intent-v1')
        self.assertEqual(bridge.Inspect(7,4),('UNAVAILABLE',None,'private_static_control'))
        self.assertEqual(bridge.Prepare(7,4,1,1,0,0,0),(False,None,'private_static_control'))
        self.assertEqual(bridge.Observe(7,4,1,1),('UNAVAILABLE',None,'private_static_control'))
        self.assertEqual((t.reads,t.playerWrites,t.plotWrites,t.gameWrites),(0,0,0,0))
        self.assertTrue({'BaiqiProphetJournal','BaiqiProphetIntentGameplay'}.issubset(h.seen))


if __name__=='__main__':unittest.main()
