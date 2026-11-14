from pathlib import Path
import unittest
from lupa.lua51 import LuaRuntime

ROOT=Path(__file__).resolve().parents[1]


class SettlementCollectorTests(unittest.TestCase):
    def setUp(self):
        self.lua=LuaRuntime(unpack_returned_tuples=True)
        self.factory=self.lua.execute((ROOT/'tools/lua/diagnostic_settlement_census.lua').read_text(encoding='utf-8'))
        self.lua.globals().NewCensus=self.factory

    def test_capacity_flat_validation_and_copies(self):
        self.lua.execute('''
local a=NewCensus(2);local r={value=1,flag=true,text='x'}
assert(a.Record(r));r.value=2
assert(a.Record({value=2}));assert(not a.Record({value=3}))
for _,v in ipairs({0/0,math.huge,-math.huge,{},function()end})do assert(not a.Record({value=v}))end
assert(not a.Record({[1]='x'}));assert(not a.Record(false))
local s=a.Snapshot();assert(s.total_calls==10 and s.invalid_rows==7 and s.dropped==1 and #s.rows==2)
assert(s.rows[1].value==1);s.rows[1].value=9;s.rows[2]={};s.enabled=false
assert(a.Snapshot().rows[1].value==1 and a.Snapshot().rows[2].value==2 and a.Snapshot().enabled)
''')

    def test_factory_validation_and_retirement_are_permanent(self):
        for cap in (0,-1,4097,1.5,float('nan'),float('inf'),'2',False,None):
            with self.subTest(cap=cap),self.assertRaises(Exception):self.factory(cap)
        self.lua.execute('''
local a=NewCensus(1);a.Stop();a.Stop();a.enabled=true
assert(not a.Record({value=1}));assert(not a.Snapshot().enabled)
a.Retire();a.Retire();local s=a.Snapshot()
assert(s.retired and not s.enabled and s.total_calls==0 and #s.rows==0)
''')

    def bind(self):
        self.lua.globals().Bind=self.lua.execute((ROOT/'tools/lua/diagnostic_settlement_runner.lua').read_text(encoding='utf-8'))
        self.lua.execute('''
a=NewCensus(10);meta=0
local function read()meta=meta+1;return 1 end
p={GetCities=function()return{GetCount=read}end}
Bind(a,{turn=read,clock=read})
''')

    def test_runner_preserves_return_arity_and_errors_then_stops_reads(self):
        self.bind();self.lua.execute('''
local result={};local f=function(_,_,_,_,_,_,_,r)assert(r);r.ai_available=true;r.hints_kind='table';return result,nil,false end
local function pack(...)return{n=select('#',...),...}end
local v=pack(a.Run(f,'recruit_choice',p,{},true,nil,nil,nil,nil))
assert(v.n==3 and v[1]==result and v[2]==nil and v[3]==false)
local ok,err=pcall(a.Run,function()error('ORIGINAL_FAILURE',0)end,'recruit_write',p,{})
assert(not ok and err=='ORIGINAL_FAILURE');assert(a.Snapshot().rows[2].failed)
local before=meta;a.Retire()
v=pack(a.Run(function(_,_,_,_,_,_,_,r)assert(r==nil);return nil,false end,'recruit_choice',p,{}))
assert(v.n==2 and v[1]==nil and v[2]==false and meta==before and #a.Snapshot().rows==2)
''')

    def test_missing_metadata_is_absent_and_never_invented_zero(self):
        self.bind();self.lua.execute('''
local bad=function()error('unavailable')end
local b=NewCensus(1);Bind(b,{turn=bad,clock=bad})
local p={GetCities=bad};b.Run(function()return{}end,'recruit_choice',p,{})
local r=b.Snapshot().rows[1]
assert(r.started==nil and r.ended==nil and r.turn_start==nil and r.cities_start==nil)
''')


if __name__=='__main__':unittest.main()
