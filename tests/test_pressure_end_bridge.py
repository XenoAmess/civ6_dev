"""Real stopwatch with fake Native events; no END or gameplay operations."""
import importlib
from pathlib import Path
import unittest

ROOT=Path(__file__).resolve().parents[1]


class PressureEndBridgeTests(unittest.TestCase):
    def case(self,initial=None,source=None,version='lua51'):
        lua=importlib.import_module('lupa.'+version).LuaRuntime(unpack_returned_tuples=True)
        lua.globals().NewClock=lua.execute((ROOT/'tools/lua/benchmark_turn_clock.lua').read_text(encoding='utf-8'))
        lua.globals().NewBridge=lua.execute((ROOT/'tools/lua/benchmark_end_bridge.lua').read_text(encoding='utf-8'))
        lua.execute('''Turn=85;Clock=10;Token=string.rep('a',32);Handlers={};ClockReads=0
ClockObject=NewClock(function()return Clock end,function()return Turn end,function()return 0 end,
 {Add=function(f)Handlers[#Handlers+1]=f end,Remove=function()end},16)
Stage={phase='RECORDING',token=Token,ends={},normal_end=true,source_version=140}
Env={ExposedMembers={},GetStage=function()return Stage end,
 GetClock=function()ClockReads=ClockReads+1;return ClockObject end,
 GetTurn=function()return Turn end,GetLocal=function()return 0 end}''')
        g=lua.globals();g.Env.source_version=source;g.Env.initial_turn=initial
        g.Stage.source_version=source if source is not None else 140
        if initial is not None:
            g.Stage.source='baiqi142-pressure-paired-v1';g.Stage.initial_turn=initial
            if type(initial) is int and 0<=initial<=2147483641:g.Turn=initial
        g.Stage.ends[g.Turn]=True;g.H=g.NewBridge(g.Env);g.Entry=g.H.entry
        return lua

    def test_all_five_actual_segments_and_legacy_fields_dual_versions(self):
        for version in ('lua51','lua53'):
            for initial,source in [(None,None),(None,142),(0,142),(1,142),(2147483641,142)]:
                lua=self.case(initial,source,version);g=lua.globals();first=85 if initial is None else initial
                self.assertTrue(g.H.active)
                self.assertEqual(g.Entry.initial_turn,initial)
                self.assertEqual(g.Entry.marker,'baiqi-paired-end-bridge-v1' if initial is None else 'baiqi-paired-end-bridge-pressure-v1')
                self.assertEqual(g.Entry.source,None if initial is None else 'baiqi142-pressure-paired-v1')
                for turn in range(first,first+5):
                    g.Turn=turn;g.Clock=100+20*(turn-first);g.Stage.ends[turn]=True
                    self.assertTrue(g.Entry.Begin(turn,g.Token))
                    g.Turn=turn+1;g.Clock+=2
                    lua.execute('for _,fn in ipairs(Handlers)do fn(0,false)end')
                records=g.ClockObject.Snapshot(g.ClockObject).records
                self.assertEqual([(r.from_turn,r.to_turn,r.seconds) for r in records.values()],
                                 [(t,t+1,2) for t in range(first,first+5)])
                self.assertEqual((g.H.errors,g.H.refused),(0,0))

    def test_invalid_constructor_never_reads_clock_or_publishes(self):
        for initial,source in [(False,142),(1.5,142),(float('nan'),142),(float('inf'),142),
                               (-1,142),(2147483642,142),(1,140),(1,None)]:
            lua=self.case(initial,source);g=lua.globals()
            self.assertFalse(g.H.active);self.assertEqual(g.H.errors,1)
            self.assertIsNone(g.H.entry);self.assertIsNone(g.Env.ExposedMembers.P6BaiqiPairEndBridge)
            self.assertEqual(g.ClockReads,0)

    def test_wrong_turn_headers_and_tampered_entry_refuse_before_begin(self):
        for target,key,value in [('Stage','source',None),('Stage','initial_turn',None),
                                  ('Entry','source','WRONG'),('Entry','initial_turn',500),('Entry','marker','WRONG')]:
            lua=self.case(1,142);g=lua.globals();g[target][key]=value
            self.assertFalse(g.Entry.Begin(1,g.Token));self.assertIsNone(g.ClockObject.Snapshot(g.ClockObject).pending)
        for turn in (0,6,85):
            lua=self.case(1,142);g=lua.globals();g.Turn=turn;g.Stage.ends[turn]=True
            self.assertFalse(g.Entry.Begin(turn,g.Token));self.assertIsNone(g.ClockObject.Snapshot(g.ClockObject).pending)

    def test_uncertain_post_begin_is_never_retried(self):
        lua=self.case(1,142)
        lua.execute('''local original=ClockObject.Snapshot;Calls=0
ClockObject.Snapshot=function(self)Calls=Calls+1;if Calls==2 then error('uncertain')end;return original(self)end
assert(not Entry.Begin(1,Token)and H.errors==1 and ClockObject:Snapshot().pending~=nil)
local before=Calls;assert(not Entry.Begin(1,Token)and Calls==before)''')

    def test_foreign_slot_and_retired_identity_preserved(self):
        lua=self.case(1,142)
        lua.execute('''local foreign={marker='foreign'};Env.ExposedMembers.P6BaiqiPairEndBridge=foreign
local bad=NewBridge(Env);assert(not bad.active and bad.errors==1)
assert(not Entry.Begin(1,Token));assert(H.Retire()and H.Retire())
assert(Env.ExposedMembers.P6BaiqiPairEndBridge==foreign and not Entry.Begin(1,Token))''')
