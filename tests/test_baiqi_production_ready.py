"""Cold-load readiness, narrowly refreshed candidates, and persisted unlock intent."""
from pathlib import Path
import unittest
from lupa.lua53 import LuaRuntime

ROOT = Path(__file__).resolve().parents[1]


def execute(lua, path):
    lua.execute((ROOT/path).read_text(encoding='utf-8'))


EVENT = '''
function TestEvent()
 local handlers={}
 return {Add=function(fn) handlers[fn]=true end,Remove=function(fn) handlers[fn]=nil end,
 Fire=function(...) for fn in pairs(handlers) do fn(...) end end,
 Count=function() local n=0;for _ in pairs(handlers) do n=n+1 end;return n end}
end
'''


class ProductionReadinessTests(unittest.TestCase):
    def setUp(self):
        self.lua = LuaRuntime(unpack_returned_tuples=True)
        for path in ('tests/lua/mock_world.lua', 'tests/lua/mock_trade.lua',
                     'tests/lua/mock_military.lua', 'tests/lua/mock_standby.lua'):
            execute(self.lua, path)
        self.lua.execute(EVENT + '''
Events.CityProductionCompleted=TestEvent()
Events.UnitAddedToMap=TestEvent();Events.UnitRemovedFromMap=TestEvent()
''')
        for name in ('BaiqiConfig', 'BaiqiPolicy', 'BaiqiPlanner', 'BaiqiController'):
            execute(self.lua, f'mod/Baiqi/Lua/{name}.lua')
        self.w = self.lua.globals().TestWorld
        self.c = self.lua.globals().BaiqiController

    def test_loading_does_not_cache_unavailable_production_or_consume_request(self):
        self.w.strategic = False
        self.w.rejectStandby = True
        self.c.RunNow()
        self.c.Update(20)
        self.assertFalse(self.c.IsAvailable())
        self.w.rejectStandby, self.w.strategic = False, True
        self.c.RunNow()
        self.assertEqual(len(self.w.cityRequests), 1)
        self.assertEqual(self.w.cityRequests[1].params[5], 302)

    def test_missing_native_readiness_fails_closed(self):
        self.lua.execute('Game.IsAllowStrategicCommands=nil')
        self.c.RunNow()
        self.assertEqual(len(self.w.cityRequests), 0)

    def test_local_unit_removal_refreshes_empire_cap_in_same_turn_foreign_event_does_not(self):
        self.w.rejectStandby = True
        self.c.RunNow(); self.c.RunNow()
        self.assertEqual(len(self.w.cityRequests), 0)
        self.lua.execute('TestWorld.armyTypes={6,5,5};Events.UnitRemovedFromMap.Fire(8,99)')
        self.c.RunNow()
        self.assertEqual(len(self.w.cityRequests), 0)
        self.lua.execute('Events.UnitRemovedFromMap.Fire(7,104)')
        self.c.RunNow()
        self.assertEqual(self.w.cityRequests[1].params[4], 206)

    def test_unlock_refresh_preserves_pending_and_same_turn_attempts(self):
        self.c.RunNow()
        self.w.strategic = False
        self.c.Update(30)
        self.w.strategic = True
        for _ in range(6):
            self.c.RefreshProduction(); self.c.RunNow()
        self.assertEqual(len(self.w.cityRequests), 2)  # One pending per city.
        self.c.Update(3)  # Both native requests remain unobserved; attempts survive.
        for _ in range(6):
            self.c.RefreshProduction(); self.c.RunNow()
        self.assertEqual(len(self.w.cityRequests), 2)

    def test_completion_and_unit_add_refresh_without_overwriting_existing_two_item_queue(self):
        self.w.rejectStandby = True
        self.c.RunNow(); self.c.RunNow()
        self.w.rejectStandby = False
        self.lua.execute('TestWorld.queues[66]={{UnitType=6},{UnitType=5}};Events.UnitAddedToMap.Fire(7,105)')
        self.c.RunNow()
        self.assertEqual((len(self.w.cityRequests), self.w.cityRequests[1].city), (1, 67))
        self.assertEqual(len(self.w.queues[66]), 2)
        self.c.Shutdown()
        self.assertEqual(self.lua.globals().Events.UnitAddedToMap.Count(), 0)
        self.assertEqual(self.lua.globals().Events.UnitRemovedFromMap.Count(), 0)


class ExecutorRecoveryTests(unittest.TestCase):
    def setUp(self):
        self.lua = LuaRuntime(unpack_returned_tuples=True)
        self.lua.execute(EVENT + '''
include=function() end
W={allowed=false,hidden=false,available=false,requests={},refresh=0,runs=0}
BaiqiConfig={interval=0.35};BaiqiAdmin={Run=function() end}
BaiqiController={IsAvailable=function() return W.allowed end,
 RefreshProduction=function() W.refresh=W.refresh+1 end,
 RunNow=function() W.runs=W.runs+1 end,Update=function() end,Shutdown=function() end}
Game={GetLocalPlayer=function() return 7 end}
GameInfo={Projects={PROJECT_BAIQI_STANDBY={Hash=302}}}
Players={[7]={GetCities=function() return {Members=function()
 return ipairs({{GetBuildQueue=function() return {CanProduce=function() return W.available end} end}})
end} end}}
UI={RequestPlayerOperation=function(_,_,params) table.insert(W.requests,params) end}
PlayerOperations={EXECUTE_SCRIPT=1}
ContextPtr={LookUpControl=function() return {IsHidden=function() return W.hidden end} end,
 SetHide=function() end,SetUpdate=function(_,fn) W.update=fn end,
 SetInitHandler=function(_,fn) W.init=fn end,SetShutdown=function(_,fn) W.shutdown=fn end}
Events={LoadGameViewStateDone=TestEvent(),PlayerTurnActivated=TestEvent(),GameCoreEventPlaybackComplete=TestEvent()}
''')
        execute(self.lua, 'mod/Baiqi/UI/BaiqiExecutor.lua')
        self.w = self.lua.globals().W

    def test_recovery_defers_until_visible_and_ready_then_actual_unlock_refreshes_once(self):
        self.lua.execute('Events.LoadGameViewStateDone.Fire()')
        self.w.update(0.35)
        self.assertEqual(len(self.w.requests), 0)
        self.w.allowed, self.w.hidden = True, True
        self.w.update(0.35)
        self.assertEqual(len(self.w.requests), 0)
        self.w.hidden = False
        self.w.update(0.35)
        self.assertTrue(self.w.requests[1].standbyUnlockNeeded)
        self.assertEqual(self.w.refresh, 0)  # Void request ACK isn't availability.
        self.w.update(0.35)
        self.assertEqual(len(self.w.requests), 1)
        self.w.available = True
        self.w.update(0.35); self.w.update(0.35)
        self.assertEqual(self.w.refresh, 1)

    def test_already_unlocked_new_game_does_not_request_another_attach(self):
        self.w.allowed, self.w.available = True, True
        self.lua.execute('Events.LoadGameViewStateDone.Fire()')
        self.assertEqual(len(self.w.requests), 1)
        self.assertIsNone(self.w.requests[1].standbyUnlockNeeded)


class GameplayMigrationTests(unittest.TestCase):
    def setUp(self):
        self.lua = LuaRuntime(unpack_returned_tuples=True)
        execute(self.lua, 'tests/lua/mock_requisition.lua')
        self.lua.execute(EVENT + '''
TestCapture.gameProps.BAIQI_WITHDRAWN_RIGHTS_CLEANED=2
BaiqiCapture={Recover=function() end}
GameEvents={BaiqiRequisition=TestEvent(),BaiqiRequisitionRecover=TestEvent(),OnGameTurnStarted=TestEvent()}
TestCapture.attaches=0
TestCapture.objects.player.AttachModifierByID=function(self,id)
 assert(id=='BAIQI_ENABLE_STANDBY')
 assert(self:GetProperty('BAIQI_STANDBY_UNLOCK_V1').stage=='SUBMITTED')
 TestCapture.attaches=TestCapture.attaches+1
 if TestCapture.throwAttach then error('unknown after native effect') end
end
''')
        for name in ('BaiqiConfig', 'BaiqiPolicy', 'BaiqiPlanner', 'BaiqiRequisition', 'BaiqiGameplay'):
            execute(self.lua, f'mod/Baiqi/Lua/{name}.lua')
        self.w = self.lua.globals().TestCapture

    def recover(self, player=7, locked=True):
        self.lua.globals().GameEvents.BaiqiRequisitionRecover.Fire(
            player, self.lua.table_from({'standbyUnlockNeeded': locked}))

    def test_explicit_locked_request_persists_intent_and_never_attaches_twice_after_reload(self):
        self.recover()
        self.assertEqual(self.w.attaches, 1)
        self.assertEqual(self.w.props.BAIQI_STANDBY_UNLOCK_V1.stage, 'RETURNED')
        execute(self.lua, 'mod/Baiqi/Lua/BaiqiGameplay.lua')
        self.recover()
        self.assertEqual(self.w.attaches, 1)

    def test_unknown_native_result_keeps_persisted_marker_and_cannot_replay(self):
        self.w.throwAttach = True
        self.recover(); self.recover()
        self.assertEqual(self.w.attaches, 1)
        self.assertEqual(self.w.props.BAIQI_STANDBY_UNLOCK_V1.stage, 'UNKNOWN')

    def test_wrong_local_player_non_baiqi_and_unlocked_request_cannot_attach(self):
        self.recover(locked=False)
        self.w.localPlayer = 3
        self.recover()
        self.w.localPlayer, self.w.leader = 7, 'LEADER_TRAJAN'
        self.recover()
        self.assertEqual(self.w.attaches, 0)
        self.assertIsNone(self.w.props.BAIQI_STANDBY_UNLOCK_V1)

    def test_inactive_multiplayer_hotseat_and_nonhuman_cannot_attach(self):
        self.w.active = False
        self.recover()
        self.w.active = True
        self.lua.execute('GameConfiguration.IsAnyMultiplayer=function() return true end')
        self.recover()
        self.lua.execute('GameConfiguration.IsAnyMultiplayer=function() return false end;GameConfiguration.IsHotseat=function() return true end')
        self.recover()
        self.lua.execute('GameConfiguration.IsHotseat=function() return false end;TestCapture.objects.player.IsHuman=function() return false end')
        self.recover()
        self.assertEqual(self.w.attaches, 0)


if __name__ == '__main__':
    unittest.main()
