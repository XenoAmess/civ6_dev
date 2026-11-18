"""Exercise actual executor scheduling and recovery state across frame boundaries."""
from pathlib import Path
import unittest
from lupa.lua51 import LuaRuntime as Lua51
from lupa.lua53 import LuaRuntime as Lua53

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / 'mod/Baiqi/UI/BaiqiExecutor.lua'
FIXTURE = r'''
include=function()end
function Event()
 local h={};return {Add=function(f)h[f]=true end,Remove=function(f)h[f]=nil end,
 Fire=function(...)for f in pairs(h)do f(...)end end}
end
W={turn=4,saved=true,allowed=true,hidden=false,available=true,sent=false,
 hudReads=0,turnReads=0,availabilityReads=0,productionReads=0,
 requests={},refreshes=0,runs=0,updates={},admins=0}
BaiqiConfig={interval=.35}
BaiqiAdmin={Run=function()W.admins=W.admins+1 end}
BaiqiController={SetTurnGuard=function(f)W.guard=f end,
 SetSettlementLoadKind=function(v)assert(type(v)=='boolean')end,
 IsAvailable=function()W.availabilityReads=W.availabilityReads+1;return W.allowed and W.guard()end,
 RefreshProduction=function()W.refreshes=W.refreshes+1 end,
 RunNow=function()W.runs=W.runs+1 end,
 Update=function(dt,allow)W.updates[#W.updates+1]={delta=dt,allow=allow}end,
 Shutdown=function()end}
Game={GetLocalPlayer=function()return 7 end,
 GetCurrentGameTurn=function()W.turnReads=W.turnReads+1;return W.turn end}
GameConfiguration={IsSavedGame=function()return W.saved end}
GameInfo={Projects={PROJECT_BAIQI_STANDBY={Hash=302}}}
Players={[7]={GetCities=function()return {Members=function()
 return ipairs({{GetBuildQueue=function()return {CanProduce=function(_,hash)
 assert(hash==302);W.productionReads=W.productionReads+1;return W.available end}end}})
 end}end}}
UI={HasSentTurnComplete=function(...)assert(select('#',...)==0);return W.sent end,
 RequestPlayerOperation=function(pid,op,p)assert(pid==7 and op==1);W.requests[#W.requests+1]=p end}
PlayerOperations={EXECUTE_SCRIPT=1}
ContextPtr={LookUpControl=function()W.hudReads=W.hudReads+1;return {IsHidden=function()return W.hidden end}end,
 SetHide=function()end,SetUpdate=function(_,f)W.update=f end,
 SetInitHandler=function(_,f)W.init=f end,SetShutdown=function(_,f)W.shutdown=f end}
Events={LoadGameViewStateDone=Event(),PlayerTurnActivated=Event(),GameCoreEventPlaybackComplete=Event()}
function ResetCounts()
 W.hudReads=0;W.turnReads=0;W.availabilityReads=0;W.productionReads=0
 W.requests={};W.refreshes=0;W.runs=0;W.updates={};W.admins=0
end
'''


class ExecutorCadenceTests(unittest.TestCase):
    def world(self, runtime=Lua53, *, available=True, saved=True):
        lua = runtime(unpack_returned_tuples=True)
        lua.execute(FIXTURE)
        w = lua.globals().W
        w.available, w.saved = available, saved
        lua.execute(SOURCE.read_text(encoding='utf-8'))
        lua.execute('Events.LoadGameViewStateDone.Fire();ResetCounts()')
        return lua, w

    def test_subinterval_frames_do_not_enter_native_or_controller(self):
        for runtime in (Lua51, Lua53):
            with self.subTest(lua=runtime.__module__):
                lua, w = self.world(runtime)
                for _ in range(60):
                    w.update(.005)
                self.assertEqual((w.hudReads, w.turnReads, w.availabilityReads,
                                  w.productionReads, len(w.updates), w.admins), (0, 0, 0, 0, 0, 0))

    def test_elapsed_is_forwarded_without_frame_loss_or_catchup_burst(self):
        lua, w = self.world()
        for _ in range(4):
            w.update(.09)
        self.assertEqual((len(w.updates), w.admins), (1, 1))
        self.assertAlmostEqual(w.updates[1].delta, .36)
        w.update(1.4)
        self.assertEqual((len(w.updates), w.admins), (2, 2))
        self.assertAlmostEqual(w.updates[2].delta, 1.4)

    def test_no_standby_poll_after_completed_recovery(self):
        lua, w = self.world()
        for _ in range(4):
            w.update(.35)
        self.assertEqual(w.productionReads, 0)
        self.assertEqual((len(w.requests), w.refreshes, len(w.updates), w.admins), (0, 0, 4, 4))

    def test_awaiting_unlock_keeps_polling_until_observed_then_stops(self):
        lua, w = self.world(available=False)
        w.update(.35)
        self.assertEqual((w.productionReads, w.refreshes, len(w.requests)), (1, 0, 0))
        w.available = True
        w.update(.35)
        self.assertEqual((w.productionReads, w.refreshes), (2, 1))
        w.update(.35)
        self.assertEqual((w.productionReads, w.refreshes, len(w.requests)), (2, 1, 0))

    def test_turn_guard_is_reread_at_flush_and_activation_is_immediate(self):
        lua, w = self.world()
        w.update(.17)
        w.turn = 5
        w.update(.18)
        self.assertEqual((len(w.requests), w.admins), (0, 0))
        self.assertIs(w.updates[1].allow, False)
        lua.execute('Events.PlayerTurnActivated.Fire(8,true)')
        self.assertEqual((len(w.requests), w.runs), (0, 0))
        lua.execute('Events.PlayerTurnActivated.Fire(7,true)')
        self.assertEqual((len(w.requests), w.runs), (1, 1))

    def test_load_and_playback_events_do_not_wait_for_periodic_timer(self):
        lua, w = self.world(saved=False)
        w.update(.1)
        self.assertEqual((len(w.requests), w.runs), (0, 0))
        lua.execute('Events.PlayerTurnActivated.Fire(7,true)')
        self.assertEqual((len(w.requests), w.runs), (1, 1))
        lua.execute('Events.GameCoreEventPlaybackComplete.Fire()')
        self.assertEqual((len(w.requests), w.runs), (1, 2))

    def test_hidden_or_unavailable_context_never_gains_cached_permission(self):
        lua, w = self.world()
        w.update(.2)
        w.hidden = True
        w.update(.2)
        self.assertEqual((len(w.updates), w.admins, len(w.requests)), (0, 0, 0))
        w.hidden, w.allowed = False, False
        w.update(.35)
        self.assertEqual((w.admins, len(w.requests)), (0, 0))
        w.allowed = True
        w.update(.35)
        self.assertEqual(w.admins, 1)

    def test_invalid_deltas_do_not_poison_future_cadence(self):
        lua, w = self.world()
        for value in (None, False, '0.4', -1, float('inf'), float('nan')):
            w.update(value)
        self.assertEqual((w.hudReads, len(w.updates)), (0, 0))
        w.update(.35)
        self.assertEqual((len(w.updates), w.admins), (1, 1))

    def test_sent_complete_blocks_orders_but_keeps_passive_update(self):
        for runtime in (Lua51, Lua53):
            with self.subTest(lua=runtime.__module__):
                lua, w = self.world(runtime)
                w.sent = True
                # This matches the real post-END state: the same acknowledged
                # turn is still active/strategic, with both busy readers false.
                lua.execute('Events.PlayerTurnActivated.Fire(7,true)')
                lua.execute('Events.GameCoreEventPlaybackComplete.Fire()')
                w.update(.35)
                self.assertEqual((len(w.requests), w.runs, w.admins), (0, 0, 0))
                self.assertEqual(len(w.updates), 1)
                self.assertIs(w.updates[1].allow, False)

    def test_unsent_next_activation_resumes_without_resetting_controller(self):
        for runtime in (Lua51, Lua53):
            with self.subTest(lua=runtime.__module__):
                lua, w = self.world(runtime)
                w.sent = True
                w.update(.35)
                self.assertEqual((w.runs, w.admins), (0, 0))
                w.turn, w.sent = 5, False
                lua.execute('Events.GameCoreEventPlaybackComplete.Fire()')
                self.assertEqual(w.runs, 0)
                lua.execute('Events.PlayerTurnActivated.Fire(7,true)')
                self.assertEqual((len(w.requests), w.runs), (1, 1))
                w.update(.35)
                self.assertEqual(w.admins, 1)
                self.assertIs(w.updates[2].allow, True)

    def test_unknown_complete_getter_never_grants_orders(self):
        getters = ('nil', 'false', 'function()error("unknown")end',
                   'function()end', 'function()return nil end',
                   'function()return false,nil end',
                   'function()return false,false end',
                   'function()return 0 end', 'function()return "false" end',
                   'function()return {} end')
        for runtime in (Lua51, Lua53):
            for getter in getters:
                with self.subTest(lua=runtime.__module__, getter=getter):
                    lua, w = self.world(runtime)
                    lua.execute('UI.HasSentTurnComplete='+getter)
                    lua.execute('Events.PlayerTurnActivated.Fire(7,true);Events.GameCoreEventPlaybackComplete.Fire()')
                    w.update(.35)
                    self.assertEqual((len(w.requests), w.runs, w.admins), (0, 0, 0))
                    self.assertIs(w.updates[1].allow, False)

    def test_turn_changed_inside_complete_read_does_not_use_old_ack(self):
        for runtime in (Lua51, Lua53):
            with self.subTest(lua=runtime.__module__):
                lua, w = self.world(runtime)
                lua.execute('UI.HasSentTurnComplete=function()W.turn=W.turn+1;return false end')
                self.assertIs(w.guard(), False)
                self.assertEqual((len(w.requests), w.runs, w.admins), (0, 0, 0))

    def test_changed_complete_binding_during_read_never_grants_orders(self):
        for runtime in (Lua51, Lua53):
            for replacement in ('UI.HasSentTurnComplete=function()return false end',
                                'UI={HasSentTurnComplete=function()return false end}'):
                with self.subTest(lua=runtime.__module__, replacement=replacement):
                    lua, w = self.world(runtime)
                    lua.execute('UI.HasSentTurnComplete=function()'+replacement+';return false end')
                    self.assertIs(w.guard(), False)

    def test_complete_query_uses_static_ui_api(self):
        for runtime in (Lua51, Lua53):
            with self.subTest(lua=runtime.__module__):
                lua, w = self.world(runtime)
                lua.execute('Players[7].HasSentTurnComplete=function()error("wrong Player API")end')
                self.assertIs(w.guard(), True)
                w.update(.35)
                self.assertEqual(w.admins, 1)

    def test_ack_changed_inside_complete_read_requires_fresh_permission(self):
        for runtime in (Lua51, Lua53):
            with self.subTest(lua=runtime.__module__):
                lua, w = self.world(runtime)
                lua.execute('''UI.HasSentTurnComplete=function()
                  if not W.changed then W.changed=true;W.turn=5;Events.PlayerTurnActivated.Fire(7,true)end
                  return false end''')
                self.assertIs(w.guard(), False)
                self.assertIs(w.guard(), True)


if __name__ == '__main__':
    unittest.main()
