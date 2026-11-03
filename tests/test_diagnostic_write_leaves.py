from pathlib import Path
import unittest
from lupa.lua53 import LuaRuntime

ROOT=Path(__file__).resolve().parents[1]


class WriteLeafTests(unittest.TestCase):
    def setUp(self):
        self.lua=LuaRuntime(unpack_returned_tuples=True)
        for name,key in [('diagnostic_queries','NewCounter'),('diagnostic_write_leaves','New')]:
            self.lua.globals()[key]=self.lua.execute((ROOT/f'tools/lua/{name}.lua').read_text(encoding='utf-8'))
        self.lua.execute('''Enabled=false;Bucket={};EnableReads=0;BucketReads=0;Calls=0
function IsEnabled() EnableReads=EnableReads+1;return Enabled end
function GetBucket() BucketReads=BucketReads+1;return Bucket end
H=New(NewCounter,IsEnabled,GetBucket)
function Native(...) Calls=Calls+1;return select('#',...),... end
function Pack(...) return {n=select('#',...),...} end''')

    def test_static_exact_forward_and_disabled_stale_handles_do_not_count(self):
        self.lua.execute('''local f=H:Static('S',Native);assert(f==H:Static('S',Native))
assert(EnableReads==0 and BucketReads==0 and Calls==0)
f();assert(Calls==1 and H.stats.counters[1].totalCalls==0)
Enabled=true;local r=Pack(f(1,nil,false,nil));assert(r.n==5 and r[1]==4 and r[4]==false)
assert(Bucket['S.Call']==1 and H.stats.counters[1].totalCalls==1)
Enabled=false;f();assert(Calls==3 and H.stats.counters[1].totalCalls==1)''')

    def test_native_method_receiver_lookup_identity_and_refresh(self):
        self.lua.execute('''local old=function(self,...) assert(self==Obj);Calls=Calls+1;return ... end
Obj={SetProperty=old};local f=H:Method('M',Obj,'SetProperty');assert(f==H:Method('M',Obj,'SetProperty'))
Obj.SetProperty=function(self) assert(self==Obj);return 'new' end
local fresh=H:Method('M',Obj,'SetProperty');assert(f~=fresh)
Enabled=true;local r=Pack(f(1,nil,false,nil));assert(r.n==4 and r[3]==false and Calls==1)
assert(fresh()=='new' and Bucket['M.Call']==2 and H.stats.entries==2)''')

    def test_native_error_object_and_metadata_errors_do_not_replay(self):
        self.lua.execute('''local E={};Enabled=true;local f=H:Static('E',function() Calls=Calls+1;error(E,0) end)
local ok,e=pcall(f);assert(not ok and e==E and Calls==1 and Bucket['E.Call']==1)
local broken=New(NewCounter,function() error(E,0) end,GetBucket)
local g=broken:Static('G',Native);assert(g()==0 and broken.stats.enabledErrors==1)
local metadata=New(NewCounter,IsEnabled,function() error(E,0) end)
assert(metadata:Static('Meta',Native)()==0 and metadata.stats.counters[1].callbackErrors==1)''')

    def test_factory_failure_missing_values_and_native_index_errors(self):
        self.lua.execute('''assert(H:Static('nil',nil)==nil and H:Static('false',false)==false)
assert(H:Method('missing',{},'Nope')==nil)
local E={};local bad=setmetatable({},{__index=function() error(E,0) end})
local ok,e=pcall(function() H:Method('bad',bad,'SetProperty') end);assert(not ok and e==E)
local h=New(function() error(E,0) end,IsEnabled,GetBucket)
local f=h:Method('fallback',{SetProperty=function(self,x) assert(type(self)=='table');return x end},'SetProperty')
assert(f(9)==9 and h.stats.wrapErrors==1 and h.stats.entries==0)''')

    def test_bound_overflow_never_stores_fallbacks_and_limits_validate(self):
        self.lua.execute('''local h=New(NewCounter,IsEnabled,GetBucket,{maxEntries=1})
local f=h:Static('one',Native)
for i=1,100 do local obj={SetProperty=function(self,x) assert(self~=nil);return x end};assert(h:Method('other',obj,'SetProperty')(i)==i) end
assert(h.stats.entries==1 and #h.stats.counters==1 and h.stats.dropped==100)
local z=New(NewCounter,IsEnabled,GetBucket,{maxEntries=0});assert(z:Static('Z',Native)==Native and z.stats.entries==0 and z.stats.dropped==1)
for _,v in ipairs({-1,0.5,4097,math.huge,0/0,false}) do assert(not pcall(function() New(NewCounter,IsEnabled,GetBucket,{maxEntries=v}) end)) end''')

    def test_real_lua_c_userdata_receiver_is_not_replaced_by_proxy(self):
        self.lua.execute('''local file=assert(io.tmpfile());assert(type(file)=='userdata')
Enabled=true;local seek=H:Method('userdata',file,'seek')
assert(seek('cur',0)==0 and Bucket['userdata.Call']==1)
file:close()''')


if __name__=='__main__':unittest.main()
