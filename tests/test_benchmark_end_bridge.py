from pathlib import Path
import unittest
from lupa.lua51 import LuaRuntime

ROOT=Path(__file__).resolve().parents[1]


class BenchmarkEndBridgeTests(unittest.TestCase):
    def setUp(self):
        self.lua=LuaRuntime(unpack_returned_tuples=True)
        for stem,name in [('benchmark_turn_clock','NewClock'),('benchmark_end_bridge','NewBridge')]:
            self.lua.globals()[name]=self.lua.execute((ROOT/f'tools/lua/{stem}.lua').read_text(encoding='utf-8'))
        self.lua.execute('''rawget=nil;rawset=nil;Token=string.rep('a',32);Turn=85;Clock=10
Handlers={};ClockObject=NewClock(function()return Clock end,function()return Turn end,function()return 0 end,
 {Add=function(f)Handlers[#Handlers+1]=f end,Remove=function()end},16)
Stage={phase='RECORDING',token=Token,ends={[85]=true},normal_end=true,source_version=140}
Env={ExposedMembers={},GetStage=function()return Stage end,GetClock=function()return ClockObject end,
 GetTurn=function()return Turn end,GetLocal=function()return 0 end}
H=NewBridge(Env);Entry=H.entry''')

    def test_real_clock_starts_after_preparation_and_keeps_stage_immutable(self):
        self.lua.execute('''assert(H.active and H.errors==0 and Entry.source_version==140)
Clock=50;assert(Entry.Begin(85,Token))
local s=ClockObject:Snapshot();assert(s.pending.started==50 and s.pending.from_turn==85)
assert(Stage.ends[85]==true and Stage.normal_end==true and Stage.source_version==140)
Turn=86;Clock=52;for _,f in ipairs(Handlers)do f(0,false)end
s=ClockObject:Snapshot();assert(#s.records==1 and s.records[1].seconds==2)
assert(H.errors==0 and H.refused==0)''')

    def test_missing_reservation_or_authorization_cannot_be_fabricated(self):
        self.lua.execute('''Stage.ends[85]=nil;Stage.normal_end=false;Stage.source_version=0
assert(not Entry.Begin(85,Token) and H.refused==1)
assert(Stage.ends[85]==nil and Stage.normal_end==false and Stage.source_version==0)
assert(ClockObject:Snapshot().pending==nil)''')

    def test_foreign_publication_stolen_identity_and_retired_cache_are_preserved(self):
        self.lua.execute('''local foreign={marker='foreign'}
Env.ExposedMembers.P6BaiqiPairEndBridge=foreign
local bad=NewBridge(Env);assert(not bad.active and bad.errors==1 and bad.entry==nil)
assert(not Entry.Begin(85,Token) and ClockObject:Snapshot().pending==nil)
assert(H.Retire() and H.Retire() and not H.active)
assert(Env.ExposedMembers.P6BaiqiPairEndBridge==foreign and not Entry.Begin(85,Token))''')

    def test_unknown_getters_cannot_throw_or_resume_a_failed_bridge(self):
        self.lua.execute('''local getter=Env.GetStage;Env.GetStage=function()error('qa')end
local ok,v=pcall(Entry.Begin,85,Token);assert(ok and not v and H.errors==1)
Env.GetStage=getter
assert(not Entry.Begin(85,Token) and ClockObject:Snapshot().pending==nil)''')

    def test_post_begin_snapshot_exception_cannot_throw_or_retry(self):
        self.lua.execute('''
local original=ClockObject.Snapshot;local n=0
ClockObject.Snapshot=function(self)n=n+1;if n==2 then error('post-begin')end;return original(self)end
assert(not Entry.Begin(85,Token) and H.errors==1 and ClockObject:Snapshot().pending~=nil)
local before=n;assert(not Entry.Begin(85,Token) and n==before)''')

    def test_invalid_tokens_turns_and_replaced_clock_cannot_begin(self):
        self.lua.execute('''for _,t in ipairs({84,90,85.5,math.huge,0/0})do assert(not Entry.Begin(t,Token))end
for _,token in ipairs({'',string.rep('A',32),string.rep('g',32),string.rep('a',31)})do
 assert(not Entry.Begin(85,token)) end
Env.GetClock=function()return {}end
assert(not Entry.Begin(85,Token) and ClockObject:Snapshot().pending==nil)''')

    def test_all_five_segments_use_once_only_clock_attempts(self):
        self.lua.execute('''for turn=85,89 do
 Turn=turn;Stage.ends[turn]=true;Clock=100+20*(turn-85)
 assert(Entry.Begin(turn,Token));Clock=Clock+2;Turn=turn+1
 for _,f in ipairs(Handlers)do f(0,false)end
end
assert(#ClockObject:Snapshot().records==5 and H.errors==0 and H.refused==0)
assert(not Entry.Begin(85,Token))''')


if __name__=='__main__':
    unittest.main()
