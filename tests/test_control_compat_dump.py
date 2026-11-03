from pathlib import Path
import unittest
from lupa.lua53 import LuaError
from test_static_control_core import CoreHarness

ROOT=Path(__file__).resolve().parents[1]
SOURCE=(ROOT/'tools/lua/control_compat_dump.lua').read_text(encoding='utf-8')


class ControlCompatDumpTests(unittest.TestCase):
    def setup_context(self):
        h=CoreHarness();h.load('BaiqiGameplay');lua=h.lua
        lua.execute('''
Game.GetLocalPlayer=function() return 0 end
Players[0]={GetCities=function() return {GetCount=function() return 10 end} end}
UI={IsGameCoreBusy=function() return false end,IsProcessingMessages=function() return false end}
''')
        new=lua.execute((ROOT/'tools/lua/benchmark_turn_clock.lua').read_text(encoding='utf-8'))
        g=lua.globals();clock=new(lua.eval('function() return 1 end'),g.Game.GetCurrentGameTurn,g.Game.GetLocalPlayer,g.Events.PlayerTurnActivated,16)
        env=lua.table_from({'Game':g.Game,'Players':g.Players,'UI':g.UI,'Clock':clock,'ExposedMembers':g.ExposedMembers})
        return h,lua.execute(SOURCE),env

    def test_six_actual_factories_metadata_only_no_bridge_calls_or_addresses(self):
        h,dump,env=self.setup_context();rows=[]
        emit=h.lua.eval('function(callback) return function(...) callback(...) end end')(lambda *args:rows.append(args))
        status=dump(env,emit)
        self.assertEqual((status.available,status.unavailable,status.context_ok,status.clock_ok),(6,0,True,True))
        self.assertEqual(len([r for r in rows if r[0]=='BRIDGE']),6)
        self.assertTrue(all('Inspect:function' in r[4] for r in rows if r[0]=='BRIDGE'))
        self.assertEqual((h.lua.globals().T.playerWrites,h.lua.globals().T.plotWrites,h.lua.globals().T.gameWrites),(0,0,0))
        clock=next(r for r in rows if r[0]=='CLOCK');self.assertEqual(clock[3],0)

    def test_userdata_like_field_exception_is_unavailable_and_others_continue(self):
        h,dump,env=self.setup_context();h.lua.execute("ExposedMembers.BaiqiCreativeIntentBridge=setmetatable({},{__index=function() error('field') end})")
        status=dump(env,h.lua.eval('function(...) end'))
        self.assertEqual((status.available,status.unavailable),(5,1))

    def test_snapshot_exception_explicit_unavailable(self):
        h,dump,env=self.setup_context();env.Clock=h.lua.eval("{Snapshot=function() error('snapshot') end}");rows=[]
        emit=h.lua.eval('function(callback) return function(...) callback(...) end end')(lambda *args:rows.append(args))
        status=dump(env,emit)
        self.assertFalse(status.clock_ok);self.assertIn(('CLOCK','UNAVAILABLE'),rows)
        self.assertEqual((status.available,status.unavailable),(0,6))

    def test_wrong_turn_returns_before_players_or_clock_or_bridges(self):
        h,dump,env=self.setup_context();h.lua.execute("Game.GetCurrentGameTurn=function() return 86 end")
        env.Players=h.lua.eval("setmetatable({},{__index=function() error('must not read') end})")
        status=dump(env,h.lua.eval('function(...) end'))
        self.assertFalse(status.context_ok);self.assertEqual((status.available,status.unavailable),(0,6))

    def test_emit_error_stops_without_swallowing(self):
        h,dump,env=self.setup_context();h.lua.execute('T.emits=0')
        emit=h.lua.eval("function(...) T.emits=T.emits+1;error('sink') end")
        with self.assertRaises(LuaError):dump(env,emit)
        self.assertEqual(h.lua.globals().T.emits,1)


if __name__=='__main__':unittest.main()
