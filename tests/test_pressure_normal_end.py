"""Real clock/bridge, fake UI only; no Native game operations."""
import importlib
import unittest
from tests import test_pressure_end_bridge as bridge_tests
from tools.paired_normal_end import request_end,request_pressure_end


class PressureNormalEndTests(unittest.TestCase):
    def case(self,first=1,version='lua51'):
        lua=bridge_tests.PressureEndBridgeTests().case(first,142,version)
        lua.execute('''ExposedMembers=Env.ExposedMembers;Actions={};ActionTypes={ACTION_ENDTURN=7}
Game={GetCurrentGameTurn=function()return Turn end,GetLocalPlayer=function()return 0 end,IsAllowStrategicCommands=function()return true end}
Players={[0]={IsTurnActive=function()return true end}}
UI={CanEndTurn=function()return true end,IsGameCoreBusy=function()return false end,IsProcessingMessages=function()return false end,
 RequestAction=function(...)assert(select('#',...)==1 and (...)==7);Actions[#Actions+1]=Turn end}''')
        calls=[]
        def query(context,code):
            self.assertEqual(context,'ActionPanel');calls.append(code);messages=[]
            lua.globals().print=lambda *args:messages.append({'tag':-1,'payload':'ActionPanel: '+'\t'.join(map(str,args))})
            lua.execute(code)
            return messages
        return lua,query,calls

    def test_five_actual_segments_and_legacy_endpoint_dual_versions(self):
        for version in ('lua51','lua53'):
            for first in (0,1,2147483641):
                lua,q,calls=self.case(first,version);g=lua.globals()
                for t in range(first,first+5):
                    g.Turn=t;g.Clock=100+20*(t-first);g.Stage.ends[t]=True
                    ack=request_pressure_end(q,t,g.Token,initial_turn=first)
                    self.assertEqual((ack['turn'],ack['initial_turn'],ack['requested'],ack['forced']),(t,first,True,False))
                    g.Turn=t+1;g.Clock+=2;lua.execute('for _,fn in ipairs(Handlers)do fn(0,false)end')
                self.assertEqual(len(calls),5);self.assertEqual(lua.eval('#Actions'),5)
                self.assertEqual([r.to_turn for r in g.ClockObject.Snapshot(g.ClockObject).records.values()],list(range(first+1,first+6)))
            lua,q,calls=self.case(None,version);g=lua.globals()
            self.assertEqual(request_end(q,85,g.Token,expected_source_version=142),dict(turn=85,token=g.Token,requested=True,forced=False))

    def test_invalid_arguments_never_query(self):
        def query(*args):self.fail('Invalid input queried')
        for t,first,token in [(1,True,'a'*32),(1,1.0,'a'*32),(1,-1,'a'*32),(1,2147483642,'a'*32),
                              (True,1,'a'*32),(0,1,'a'*32),(6,1,'a'*32),(1,1,'A'*32),(1,1,None)]:
            with self.assertRaises(ValueError):request_pressure_end(query,t,token,initial_turn=first)

    def test_every_ui_guard_and_header_refuses_before_action(self):
        changes=["Turn=2","Game.GetLocalPlayer=function()return 1 end","Players[0].IsTurnActive=function()return false end",
                 "Game.IsAllowStrategicCommands=function()return false end","UI.CanEndTurn=function()return false end",
                 "UI.IsGameCoreBusy=function()return true end","UI.IsProcessingMessages=function()return true end",
                 "Entry.marker='wrong'","Entry.source='wrong'","Entry.source_version=140","Entry.initial_turn=2","Entry.Begin=nil"]
        for change in changes:
            lua,q,calls=self.case();lua.execute(change)
            with self.assertRaises(importlib.import_module('lupa.lua51').LuaError):request_pressure_end(q,1,'a'*32,initial_turn=1)
            self.assertEqual(len(calls),1);self.assertEqual(lua.eval('#Actions'),0)
            self.assertIsNone(lua.globals().ClockObject.Snapshot(lua.globals().ClockObject).pending)

    def test_cross_mode_and_duplicate_cannot_issue_second_action(self):
        lua,q,calls=self.case(85)
        with self.assertRaises(importlib.import_module('lupa.lua51').LuaError):request_end(q,85,'a'*32,expected_source_version=142)
        lua,q,calls=self.case(None)
        with self.assertRaises(importlib.import_module('lupa.lua51').LuaError):request_pressure_end(q,85,'a'*32,initial_turn=85)
        lua,q,calls=self.case();request_pressure_end(q,1,'a'*32,initial_turn=1)
        with self.assertRaises(importlib.import_module('lupa.lua51').LuaError):request_pressure_end(q,1,'a'*32,initial_turn=1)
        self.assertEqual(len(calls),2);self.assertEqual(lua.eval('#Actions'),1)

    def test_unknown_ack_and_transport_after_action_are_not_retried(self):
        for mode in ('missing','wrong','transport'):
            lua,q,calls=self.case()
            def broken(context,code):
                messages=q(context,code)
                if mode=='transport':raise OSError('after action')
                if mode=='missing':return []
                return [{'tag':-1,'payload':'ActionPanel: P6_PRESSURE_PAIR_ORDINARY_ISSUED\t1\t'+'b'*32+'\t1'}]
            with self.assertRaises((RuntimeError,OSError)):request_pressure_end(broken,1,'a'*32,initial_turn=1)
            self.assertEqual(len(calls),1);self.assertEqual(lua.eval('#Actions'),1)
            self.assertEqual(lua.globals().ClockObject.Snapshot(lua.globals().ClockObject).pending.from_turn,1)
