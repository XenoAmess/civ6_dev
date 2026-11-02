"""Read-only telemetry must preserve static native function behavior."""
from pathlib import Path
import unittest
from lupa.lua53 import LuaRuntime

SOURCE = Path(__file__).resolve().parents[1] / "tools/lua/diagnostic_queries.lua"


class DiagnosticQueryTests(unittest.TestCase):
    def setUp(self):
        self.lua = LuaRuntime(unpack_returned_tuples=True)
        self.lua.execute("""
unpack=table.unpack;table.pack=nil;table.unpack=nil;debug=nil
function Pack(...) return {n=select('#',...),...} end
calls=0;getterCalls=0;bucket={}
function Bucket() getterCalls=getterCalls+1;return bucket end
NativeResult=setmetatable({},{__index={marker=88}})
Original=setmetatable({
 A=function(...) calls=calls+1;return NativeResult,nil,false,... end,
 B=function(...) calls=calls+1;return 'B',... end,
 keep=false
},{__index={inherited='native'}})
""")
        self.lua.globals().NewCounter = self.lua.execute(SOURCE.read_text(encoding="utf-8"))

    def check_lua(self, code):
        self.lua.execute(code)

    def test_binding_does_not_call_or_modify_original_namespace(self):
        self.check_lua("""
local a,b=Original.A,Original.B
local proxy,s=NewCounter(Original,{'A','B'},'Map',Bucket)
assert(calls==0 and getterCalls==0 and Original.A==a and Original.B==b)
assert(proxy~=Original and proxy.keep==false and proxy.inherited=='native')
assert(getmetatable(proxy).__index==Original and s.totalCalls==0)
""")

    def test_distinct_loop_closures_count_the_correct_function(self):
        self.check_lua("""
local proxy,s=NewCounter(Original,{'A','B'},'Map',Bucket)
assert(proxy.A()==NativeResult and proxy.B()=='B' and proxy.B()=='B')
assert(calls==3 and getterCalls==3 and bucket['Map.A']==1 and bucket['Map.B']==2)
assert(s.totalCalls==3 and s.callbackErrors==0)
""")

    def test_native_object_and_variadic_nil_false_values_are_preserved(self):
        self.check_lua("""
Original.A=function(...)
 calls=calls+1;local r=Pack(...)
 assert(r.n==15 and r[1]==false and r[3]==nil and r[14]==14 and r[15]==nil)
 return NativeResult,nil,false,4,5,6,7,8,9,10,11,12,nil,14,nil
end
local proxy,s=NewCounter(Original,{'A'},'Map',Bucket)
local r=Pack(proxy.A(false,2,nil,4,5,6,7,8,9,10,11,12,nil,14,nil))
assert(r.n==15 and r[1]==NativeResult and r[1].marker==88 and r[2]==nil and r[3]==false and r[14]==14 and r[15]==nil)
assert(calls==1 and s.totalCalls==1 and s.callbackErrors==0)
""")

    def test_nil_bucket_is_normal_outside_observed_scope(self):
        self.check_lua("""
local proxy,s=NewCounter(Original,{'A'},'Map',function() getterCalls=getterCalls+1 end)
assert(proxy.A()==NativeResult and getterCalls==1 and calls==1)
assert(s.totalCalls==1 and s.callbackErrors==0 and next(bucket)==nil)
""")

    def test_getter_error_or_wrong_bucket_never_suppresses_original(self):
        self.check_lua("""
local failure={}
for _,getter in ipairs({function() error(failure,0) end,function() return 'wrong' end}) do
 local proxy,s=NewCounter(Original,{'A'},'Map',getter);local before=calls
 assert(proxy.A()==NativeResult and calls==before+1)
 assert(s.callbackErrors==1 and s.totalCalls==1 and next(failure)==nil)
end
""")

    def test_invalid_counter_is_retained_and_does_not_block_original(self):
        self.check_lua("""
for _,value in ipairs({false,'wrong',-1,.5,0/0,math.huge,-math.huge,1e308}) do
 local b={['Map.A']=value}
 local proxy,s=NewCounter(Original,{'A'},'Map',function() return b end);local before=calls
 assert(proxy.A()==NativeResult and calls==before+1 and s.callbackErrors==1)
 if type(value)=='number' and value~=value then assert(b['Map.A']~=b['Map.A']) else assert(b['Map.A']==value) end
end
""")

    def test_counter_metatable_errors_are_observational_only(self):
        self.check_lua("""
for _,meta in ipairs({
 {__index=function() error('getter failed',0) end},
 {__newindex=function() error('setter failed',0) end}
}) do
 local b=setmetatable({},meta)
 local proxy,s=NewCounter(Original,{'A'},'Map',function() return b end);local before=calls
 assert(proxy.A()==NativeResult and calls==before+1 and s.callbackErrors==1)
end
""")

    def test_original_error_is_not_swallowed_by_the_observer(self):
        self.check_lua("""
local failure={}
Original.A=function() calls=calls+1;error(failure,0) end
local proxy,s=NewCounter(Original,{'A'},'Map',Bucket)
local ok,err=pcall(proxy.A)
assert(not ok and err==failure and calls==1 and bucket['Map.A']==1)
assert(s.totalCalls==1 and s.callbackErrors==0)
""")

    def test_invalid_binding_is_rejected_without_probing_original(self):
        self.check_lua("""
assert(not pcall(NewCounter,Original,{'missing'},'Map',Bucket))
assert(not pcall(NewCounter,Original,{false},'Map',Bucket))
assert(not pcall(NewCounter,nil,{'A'},'Map',Bucket))
assert(not pcall(NewCounter,Original,false,'Map',Bucket))
assert(not pcall(NewCounter,Original,{'A'},false,Bucket))
assert(not pcall(NewCounter,Original,{'A'},'Map',nil))
assert(calls==0 and getterCalls==0 and next(bucket)==nil)
""")


if __name__ == "__main__":
    unittest.main()
